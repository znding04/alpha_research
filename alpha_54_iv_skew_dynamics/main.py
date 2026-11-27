#!/usr/bin/env python3
"""IV Skew Dynamics alpha signal — alpha_54.

Signal: put-call IV skew at ~30 DTE using fixed moneyness, plus its cross-sectional
dynamics (skew change vs forward returns).
  skew = IV(put strike ≈ 95% of spot) − IV(call strike ≈ 105% of spot)
Interpretation:
  skew > 0  → put IV richer than call IV → downside tail fear (skew bid)
  skew < 0  → call IV richer than put IV → upside call demand / complacency
Cross-sectionally: rank tickers by skew level; persist snapshots so skew *change*
(Δskew over ~5 days) can be scored vs forward returns.

Robustness (distinct from delta-solved risk-reversal alphas 02/42/51):
- Fixed moneyness strikes only — no Black-Scholes delta root-finding, no BS dependency.
- If an exact moneyness strike is missing, fall back to the nearest valid strike within
  a tolerance band.
- If the moneyness band is empty, fall back to nearest OTM strikes on each side.
- No reliance on delta columns (yfinance `impliedVolatility` is the only IV source).

Files:
- main.py — computes skew for 6 focus tickers, writes data/iv_skew_54_latest.csv
- ic_analysis.py — IC vs 5-day forward returns on skew level and skew change
- notes.md — hypothesis, rationale, design, results, caveats

Signal history is persisted to data/iv_skew_54_history.json so 5-day skew change
is computable once ≥2 snapshots exist (and forward-return IC once returns exist).
"""

import os
import sys
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf

from common.universe import FOCUS_TICKERS

# Target ~30DTE expiration window (30 ± 8 days)
TARGET_DTE = 30
DTE_WINDOW = 8

# Fixed moneyness offsets for skew: OTM put below spot, OTM call above spot
PUT_MONEYNESS = 0.95   # put strike ≈ 95% of spot
CALL_MONEYNESS = 1.05  # call strike ≈ 105% of spot

# Liquidity + IV sanity filters
MIN_LIQUID_VOLUME = 5
MIN_LIQUID_OI = 50
IV_MIN = 0.05
IV_MAX = 3.0

# Tolerance band (fraction of spot) for "nearest strike" fallback
STRIKE_TOL = 0.03  # ±3%

HISTORY_PATH = "data/iv_skew_54_history.json"
OUTPUT_PATH = "data/iv_skew_54_latest.csv"


def find_exp_by_dte(tq, target_dte=TARGET_DTE, window=DTE_WINDOW):
    """Find the expiration closest to target_dte (within ±window days)."""
    try:
        expirations = list(tq.options)
    except Exception:
        return None, None
    now = datetime.now()
    best = None
    best_dte = None
    for e in expirations:
        try:
            d = datetime.strptime(e, "%Y-%m-%d")
            dte = (d.date() - now.date()).days
            if dte > 0 and abs(dte - target_dte) <= window:
                if best is None or abs(dte - target_dte) < abs(best_dte - target_dte):
                    best = e
                    best_dte = dte
        except ValueError:
            continue
    return best, best_dte


def get_liquid_chain(tq, exp_str, current_price):
    """Load calls+puts chain for an expiration, apply liquidity + IV sanity filters."""
    try:
        chain = tq.option_chain(exp_str)
    except Exception:
        return None
    df = pd.concat([chain.calls, chain.puts], ignore_index=True)
    if df.empty:
        return None
    df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
    df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
    df = df[
        ((df['volume'] > MIN_LIQUID_VOLUME) | (df['openInterest'] > MIN_LIQUID_OI)) &
        (df['impliedVolatility'].notna()) &
        (df['impliedVolatility'] > IV_MIN) &
        (df['impliedVolatility'] < IV_MAX) &
        (df['lastPrice'] > 0)
    ].copy()
    if df.empty:
        return None
    return df


def nearest_strike_iv(df, option_type, target_strike):
    """Return IV of the contract nearest target_strike within tolerance band.

    option_type: 'call' or 'put'. Returns float IV or None if no valid strike.
    Fallback order: (1) nearest strike within STRIKE_TOL band of target,
                    (2) nearest valid OTM strike on the correct side of spot
                      (put: strike < spot; call: strike > spot).
    """
    side = df[df['contractSymbol'].str.contains(f'{option_type} ', na=False)] if 'contractSymbol' in df.columns else None
    # Simpler: filter by right using strike relative to spot; we don't trust contractSymbol naming.
    if option_type == 'call':
        candidates = df[df['strike'] > current_price_global]
    else:
        candidates = df[df['strike'] < current_price_global]
    if candidates.empty:
        return None
    # Primary: strikes within tolerance band of target
    band = candidates[abs(candidates['strike'] - target_strike) <= STRIKE_TOL * current_price_global]
    if not band.empty:
        return float(band.loc[abs(band['strike'] - target_strike).idxmin(), 'impliedVolatility'])
    # Fallback: nearest OTM strike to target on the correct side
    idx = (candidates['strike'] - target_strike).abs().idxmin()
    return float(candidates.loc[idx, 'impliedVolatility'])


current_price_global = None  # set per ticker inside compute_signal


def compute_signal(ticker_str):
    """Compute IV skew for a single ticker."""
    global current_price_global
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        current_price_global = current_price

        exp_str, dte = find_exp_by_dte(tq)
        if exp_str is None:
            return None

        chain = get_liquid_chain(tq, exp_str, current_price)
        if chain is None:
            return None

        target_put = current_price * PUT_MONEYNESS
        target_call = current_price * CALL_MONEYNESS

        put_iv = nearest_strike_iv(chain, 'put', target_put)
        call_iv = nearest_strike_iv(chain, 'call', target_call)

        if put_iv is None or call_iv is None:
            return None

        skew = put_iv - call_iv

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'exp': exp_str,
            'dte': int(dte),
            'put_strike_target': round(target_put, 2),
            'call_strike_target': round(target_call, 2),
            'put_iv': round(put_iv, 4),
            'call_iv': round(call_iv, 4),
            'skew': round(skew, 4),
            'skew_bps': round(skew * 10000, 1),  # basis points
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history):
    os.makedirs("data", exist_ok=True)
    with open(HISTORY_PATH, 'w') as f:
        json.dump(history, f, indent=2)


def append_snapshot(results):
    """Append today's snapshot to history, keep last 90 days, return history."""
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    snapshot = {"date": today, "signals": results}
    # Replace entry for today if present (idempotent re-runs)
    history = [h for h in history if h.get("date") != today]
    history.append(snapshot)
    history = history[-90:]  # cap at ~3 months
    save_history(history)
    return history


def compute_skew_change(history, ticker, days_back=5):
    """Compute skew change vs `days_back` ago for a ticker from persisted history."""
    if len(history) < 2:
        return None
    today = history[-1]
    today_sig = {s['ticker']: s for s in today.get("signals", [])}
    today_skew = today_sig.get(ticker, {}).get("skew")
    if today_skew is None:
        return None
    # find snapshot `days_back` ago (or the earliest if fewer)
    ref_idx = max(0, len(history) - 1 - days_back)
    ref_sig = {s['ticker']: s for s in history[ref_idx].get("signals", [])}
    ref_skew = ref_sig.get(ticker, {}).get("skew")
    if ref_skew is None:
        return None
    return today_skew - ref_skew


if __name__ == "__main__":
    print(f"\n📉 IV Skew Dynamics Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"skew = IV(put ≈ 95% spot) − IV(call ≈ 105% spot) at ~{TARGET_DTE} DTE")
    print("=" * 70)

    results = []
    for t in FOCUS_TICKERS:
        r = compute_signal(t)
        if r:
            results.append(r)
            print(f"  ✅ {t}: skew={r['skew']:.4f} ({r['skew_bps']:+.1f} bps), "
                  f"exp={r['exp']} dte={r['dte']}, put IV={r['put_iv']:.4f}, call IV={r['call_iv']:.4f}")
        else:
            print(f"  ⚠️ {t}: no data")

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print("\n" + df.to_string(index=False))

    # Persist snapshot + compute skew change vs recent history
    history = append_snapshot(results)
    print(f"\n📜 Skew history snapshots: {len(history)} (cap 90)")
    for r in results:
        chg = compute_skew_change(history, r['ticker'])
        print(f"   {r['ticker']}: skew={r['skew']:+.4f}  Δ5d={chg:+.4f}" if chg is not None else f"   {r['ticker']}: skew={r['skew']:+.4f}  Δ5d=N/A (need ≥2 snapshots)")

    print("\n💡 Interpretation:")
    print("   skew > 0  → put IV richer than call IV → downside fear (skew bid)")
    print("   skew < 0  → call IV richer → upside demand / complacency")
    print("   Δskew rising → fear building; Δskew falling → fear dissipating")

    os.makedirs("data", exist_ok=True)
    out_cols = ['ticker', 'current_price', 'exp', 'dte', 'put_iv', 'call_iv',
                'skew', 'skew_bps', 'put_strike_target', 'call_strike_target']
    df[out_cols].to_csv(OUTPUT_PATH, index=False)
    print(f"\n✅ Saved to {OUTPUT_PATH}")
    print(f"   History → {HISTORY_PATH}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")
