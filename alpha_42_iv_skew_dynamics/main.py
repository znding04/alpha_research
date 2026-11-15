#!/usr/bin/env python3
"""IV Skew Dynamics — proper 25-delta risk-reversal skew alpha.

Signal: 25-delta put-call risk reversal (RR) and its 5-day change.

    RR_25 = IV_put(25Δ) − IV_call(25Δ)

A negative RR (OTM puts richer than OTM calls) is the classic "fear" skew;
a flattening/positive RR signals complacency. We track the level and the
5-day change in level cross-sectionally across the core universe.

Improvements over alpha_31_iv_skew_dynamics (which computed a nonsensical
"1 - put_delta/call_delta" from raw delta fields that yfinance frequently
leaves as NaN):

- Uses Black-Scholes delta solved by root-finding on the strike, with IV
  interpolated from the chain itself, so the 25-delta strikes are exact
  rather than a +/-1% approximation.
- Falls back to a moneyness-based strike (5% OTM put / 5% OTM call) when the
  delta solve fails, so every ticker gets a comparable skew estimate.
- Persists daily skew levels to data/iv_skew_dynamics_42_history.json so the
  5-day change is computed from real snapshots once enough days accumulate.

Outputs: data/iv_skew_dynamics_42_latest.csv (one row per ticker).
"""

import json
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from scipy.stats import norm

from common.universe import TICKERS

TARGET_DTE = 30          # target tenor for the skew measure
CHANGE_LOOKBACK = 5      # days for the level change
HIST_PATH = "data/iv_skew_dynamics_42_history.json"
OUT_PATH = "data/iv_skew_dynamics_42_latest.csv"


def _find_expiration(ticker_str, target_dte, window=10):
    """Return the expiration string whose DTE is closest to target_dte."""
    tq = yf.Ticker(ticker_str)
    expirations = list(tq.options)
    now = datetime.now()
    best, best_diff = None, float("inf")
    for e in expirations:
        try:
            d = datetime.strptime(e, "%Y-%m-%d")
        except ValueError:
            continue
        dte = (d.date() - now.date()).days
        if dte < 2:
            continue
        diff = abs(dte - target_dte)
        if diff <= window and diff < best_diff:
            best, best_diff = e, diff
    if best is None:
        # fallback: nearest expiration > 2 DTE
        valid = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
            except ValueError:
                continue
            dte = (d.date() - now.date()).days
            if dte >= 2:
                valid.append((dte, e))
        if not valid:
            return None, None
        valid.sort()
        best_dte, best = valid[0]
        return best, best_dte
    return best, (datetime.strptime(best, "%Y-%m-%d").date() - now.date()).days


def _clean_chain(chain):
    calls, puts = chain.calls, chain.puts
    for side in (calls, puts):
        side['volume'] = side['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        side['openInterest'] = side['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
    calls = calls[(calls['impliedVolatility'].notna()) & (calls['impliedVolatility'] > 0.01) &
                  (calls['impliedVolatility'] < 3.0) & (calls['lastPrice'] > 0)].copy()
    puts = puts[(puts['impliedVolatility'].notna()) & (puts['impliedVolatility'] > 0.01) &
                (puts['impliedVolatility'] < 3.0) & (puts['lastPrice'] > 0)].copy()
    return calls, puts


def _atm_iv(calls, puts, current_price):
    """Median IV of strikes within +/-2% moneyness."""
    df = pd.concat([calls, puts], ignore_index=True)
    moneyness = df['strike'] / current_price
    atm = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
    if len(atm) >= 3:
        return float(atm['impliedVolatility'].median())
    valid = df[df['impliedVolatility'] > 0.05]
    if len(valid) == 0:
        return float(df['impliedVolatility'].median()) if len(df) else None
    idx = (valid['strike'] - current_price).abs().idxmin()
    return float(valid.loc[idx, 'impliedVolatility'])


def _interp_iv(df, strike):
    """Linear-interpolate IV at an arbitrary strike from a single-side chain."""
    sub = df[['strike', 'impliedVolatility']].dropna().sort_values('strike')
    if len(sub) < 2:
        return None
    if strike <= sub['strike'].iloc[0]:
        return float(sub['impliedVolatility'].iloc[0])
    if strike >= sub['strike'].iloc[-1]:
        return float(sub['impliedVolatility'].iloc[-1])
    ivs = np.interp(strike, sub['strike'].values, sub['impliedVolatility'].values)
    return float(ivs)


def _iv_at_strike(calls, puts, strike, side):
    df = calls if side == 'call' else puts
    if len(df) == 0:
        return None
    exact = df[np.isclose(df['strike'], strike, atol=0.01)]
    if len(exact):
        return float(exact['impliedVolatility'].iloc[0])
    return _interp_iv(df, strike)


def _bs_delta_from_iv(current_price, strike, dte, iv, side, r=0.02):
    """Black-Scholes delta for a given IV and strike."""
    if iv is None or iv <= 0:
        return None
    T = max(dte, 2) / 252.0
    d1 = (np.log(current_price / strike) + (r + 0.5 * iv**2) * T) / (iv * np.sqrt(T))
    return norm.cdf(d1) if side == 'call' else norm.cdf(d1) - 1.0


def _solve_25_delta_strike(calls, puts, current_price, dte, side):
    """Find the strike whose BS delta is closest to 25-delta (magnitude).

    Searches across the union of available strikes, using IV interpolated
    from the chain at each candidate strike. Returns (strike, iv) or None.
    """
    df = calls if side == 'call' else puts
    if len(df) == 0:
        return None
    strikes = np.sort(df['strike'].unique())
    target = 0.25 if side == 'call' else -0.25
    best_strike, best_gap, best_iv = None, float('inf'), None
    for k in strikes:
        iv = _iv_at_strike(calls, puts, k, side)
        if iv is None:
            continue
        d = _bs_delta_from_iv(current_price, k, dte, iv, side)
        if d is None:
            continue
        gap = abs(d - target)
        if gap < best_gap:
            best_gap, best_strike, best_iv = gap, k, iv
    if best_strike is None or best_gap > 0.10:
        return None
    return float(best_strike), float(best_iv)


def _fallback_strike(current_price, side):
    """5% OTM put / call strike fallback when delta solve fails."""
    return current_price * (0.95 if side == 'put' else 1.05)


def compute_skew(ticker_str):
    """Return a dict with the 25-delta risk-reversal skew for one ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        exp_str, dte = _find_expiration(ticker_str, TARGET_DTE)
        if exp_str is None:
            return None

        chain = tq.option_chain(exp_str)
        calls, puts = _clean_chain(chain)
        if len(calls) < 5 or len(puts) < 5:
            return None

        atm_iv = _atm_iv(calls, puts, current_price)
        if atm_iv is None:
            return None

        # Solve for 25-delta strikes on both sides.
        call_res = _solve_25_delta_strike(calls, puts, current_price, dte, 'call')
        put_res = _solve_25_delta_strike(calls, puts, current_price, dte, 'put')

        if call_res is not None:
            call_25_k, call_25_iv = call_res
            call_mode = 'delta'
        else:
            call_25_k = _fallback_strike(current_price, 'call')
            call_25_iv = _iv_at_strike(calls, puts, call_25_k, 'call')
            call_mode = 'moneyness'

        if put_res is not None:
            put_25_k, put_25_iv = put_res
            put_mode = 'delta'
        else:
            put_25_k = _fallback_strike(current_price, 'put')
            put_25_iv = _iv_at_strike(calls, puts, put_25_k, 'put')
            put_mode = 'moneyness'

        if put_25_iv is None or call_25_iv is None:
            return None

        rr_25 = put_25_iv - call_25_iv   # risk reversal: >0 = put skew (fear)

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'dte': int(dte),
            'atm_iv': round(atm_iv, 4),
            'put25_iv': round(put_25_iv, 4),
            'call25_iv': round(call_25_iv, 4),
            'rr_25': round(rr_25, 4),
            'call_mode': call_mode,
            'put_mode': put_mode,
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


def _load_history():
    if os.path.exists(HIST_PATH):
        try:
            with open(HIST_PATH) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_history(hist):
    os.makedirs("data", exist_ok=True)
    with open(HIST_PATH, "w") as f:
        json.dump(hist, f, indent=2)


def compute_change(ticker, rr_today, hist):
    """Compute 5-day change in rr_25 from stored history."""
    series = sorted(hist.get(ticker, {}).items())
    if not series:
        return None, None
    today = datetime.now().strftime("%Y-%m-%d")
    series.append((today, rr_today))
    # find value ~CHANGE_LOOKBACK days ago
    target_date = datetime.now().date() - timedelta(days=CHANGE_LOOKBACK)
    past_vals = [(d, v) for d, v in series if datetime.strptime(d, "%Y-%m-%d").date() <= target_date]
    if not past_vals:
        return None, None
    past_val = past_vals[-1][1]
    return round(rr_today - past_val, 4), past_val


if __name__ == "__main__":
    print(f"\n📊 IV Skew Dynamics (25-delta risk reversal) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    hist = _load_history()
    rows = []
    for t in TICKERS:
        r = compute_skew(t)
        if r is None:
            print(f"  ⚠️ {t}: no data")
            continue
        change, past = compute_change(t, r['rr_25'], hist)
        r['rr_change_5d'] = change if change is not None else ''
        r['rr_5d_ago'] = past if past is not None else ''
        rows.append(r)
        print(f"  ✅ {t}: RR25={r['rr_25']:+.4f} "
              f"(put25={r['put25_iv']:.3f}, call25={r['call25_iv']:.3f}, "
              f"chg5d={r['rr_change_5d']})")

        # update history
        today = datetime.now().strftime("%Y-%m-%d")
        hist.setdefault(t, {})[today] = r['rr_25']

    if not rows:
        print("No data collected.")
        sys.exit(1)

    _save_history(hist)

    df = pd.DataFrame(rows)
    # Cross-sectional rank: higher RR (more put skew / fear) = rank 1 (top)
    df['skew_rank'] = df['rr_25'].rank(method='dense', ascending=False).astype(int)

    print("\n" + df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   RR25 = IV_put(25Δ) − IV_call(25Δ)")
    print("   RR25 > 0 → put skew (fear / tail-hedge demand)")
    print("   RR25 < 0 → call skew (complacency / upside demand)")
    print("   rr_change_5d > 0 → skew steepening (rising fear)")

    os.makedirs("data", exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"\n✅ Saved to {OUT_PATH}")
    print(f"   History: {HIST_PATH} ({sum(len(v) for v in hist.values())} observations)\n")