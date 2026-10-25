#!/usr/bin/env python3
"""IV Skew Momentum (Refined) — 5-day change in 25-delta put-call skew.

Refinement over alpha_13:
- Uses Black-Scholes delta for strike selection (not fixed moneyness)
- Computes 25-delta put IV and 25-delta call IV via interpolation
- Skew = Call_IV(25Δ) - Put_IV(25Δ)  [positive = call skew, negative = put skew]
- Signal = 5-day change in skew (requires accumulated snapshots)
- Cross-sectionally: rising put skew (more negative) → downside hedge demand → predict lower returns
- Cross-sectionally: rising call skew → upside speculation → predict higher returns

Signal: Δ(skew) over 5 trading days. Positive Δ(skew) = call skew increasing.
Cross-section: rank tickers by Δ(skew); low (put skew rising) → short, high (call skew rising) → long.

Notes:
- This is a live signal: runs on today's yfinance option chains.
- Skew change requires daily snapshots (see ic_analysis.py for forward-return IC).
- History: data/iv_skew_momentum_refined_latest.csv
"""

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


def bs_delta(S, K, T, r, sigma, q=0.0, option_type='call'):
    """Black-Scholes delta."""
    if T <= 0 or sigma <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    if option_type == 'call':
        return float(norm.cdf(d1))
    else:
        return float(norm.cdf(d1) - 1)


def implied_vol_from_mid(ticker_str, strike, exp_date, option_type, current_price, r=0.04):
    """Rough implied vol estimate from mid price (for delta calc seed)."""
    try:
        tq = yf.Ticker(ticker_str)
        chain = tq.option_chain(exp_date)
        df = chain.calls if option_type == 'call' else chain.puts
        row = df[df['strike'] == strike]
        if len(row) == 0:
            return np.nan
        mid = (row['bid'].values[0] + row['ask'].values[0]) / 2
        if mid <= 0:
            return np.nan
        T = (datetime.strptime(exp_date, "%Y-%m-%d") - datetime.now()).days / 252
        if T <= 0:
            return np.nan
        # Simple bisection for IV
        low, high = 0.01, 3.0
        for _ in range(30):
            mid_sigma = (low + high) / 2
            d1 = (np.log(current_price / strike) + (r + 0.5 * mid_sigma**2) * T) / (mid_sigma * np.sqrt(T))
            d2 = d1 - mid_sigma * np.sqrt(T)
            if option_type == 'call':
                price = current_price * norm.cdf(d1) - strike * np.exp(-r * T) * norm.cdf(d2)
            else:
                price = strike * np.exp(-r * T) * norm.cdf(-d2) - current_price * norm.cdf(-d1)
            if price > mid:
                high = mid_sigma
            else:
                low = mid_sigma
        return (low + high) / 2
    except Exception:
        return np.nan


def compute_25d_skew(ticker_str, target_dte_range=(14, 60), r=0.04):
    """Compute 25-delta put-call skew for a ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        S = info.get('currentPrice') or info.get('regularMarketPrice')
        if S is None or S <= 0:
            return np.nan, np.nan, np.nan

        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 14 <= dte <= 60:
                    valid_exps.append((dte, e))
            except ValueError:
                continue
        if not valid_exps:
            return np.nan, np.nan, np.nan

        # Pick expiration closest to 30 DTE
        target_dte, target_exp = min(valid_exps, key=lambda x: abs(x[0] - 30))

        chain = tq.option_chain(target_exp)
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        # Filter liquid options
        for df in (calls, puts):
            df['volume'] = df['volume'].fillna(0).astype(float)
            df['openInterest'] = df['openInterest'].fillna(0).astype(float)
            df['impliedVolatility'] = pd.to_numeric(df['impliedVolatility'], errors='coerce')

        calls = calls[(calls['volume'] > 10) | (calls['openInterest'] > 100)]
        puts = puts[(puts['volume'] > 10) | (puts['openInterest'] > 100)]
        calls = calls[(calls['impliedVolatility'] > 0.01) & (calls['impliedVolatility'] < 3.0)]
        puts = puts[(puts['impliedVolatility'] > 0.01) & (puts['impliedVolatility'] < 3.0)]

        if len(calls) < 3 or len(puts) < 3:
            return np.nan, np.nan, np.nan

        T = target_dte / 252

        # Find 25-delta call and put via interpolation on IV vs delta
        # For calls: find strikes bracketing 0.25 delta
        call_iv_by_strike = calls.set_index('strike')['impliedVolatility'].sort_index()
        put_iv_by_strike = puts.set_index('strike')['impliedVolatility'].sort_index()

        # Compute deltas for each strike using its IV
        call_deltas = {}
        for K, iv in call_iv_by_strike.items():
            call_deltas[K] = bs_delta(S, K, T, r, iv, option_type='call')
        put_deltas = {}
        for K, iv in put_iv_by_strike.items():
            put_deltas[K] = abs(bs_delta(S, K, T, r, iv, option_type='put'))

        if not call_deltas or not put_deltas:
            return np.nan, np.nan, np.nan

        # Interpolate IV at 25-delta
        call_strikes = sorted(call_deltas.keys())
        call_deltas_vals = [call_deltas[k] for k in call_strikes]
        call_ivs = [call_iv_by_strike[k] for k in call_strikes]

        put_strikes = sorted(put_deltas.keys())
        put_deltas_vals = [put_deltas[k] for k in put_strikes]
        put_ivs = [put_iv_by_strike[k] for k in put_strikes]

        # Need deltas bracketing 0.25
        call_iv_25d = np.interp(0.25, call_deltas_vals[::-1], call_ivs[::-1]) if min(call_deltas_vals) < 0.25 < max(call_deltas_vals) else np.nan
        put_iv_25d = np.interp(0.25, put_deltas_vals, put_ivs) if min(put_deltas_vals) < 0.25 < max(put_deltas_vals) else np.nan

        if np.isnan(call_iv_25d) or np.isnan(put_iv_25d):
            return np.nan, np.nan, np.nan

        skew = call_iv_25d - put_iv_25d  # positive = call skew, negative = put skew
        return float(skew), float(call_iv_25d), float(put_iv_25d)

    except Exception as e:
        print(f"  ⚠️ {ticker_str} skew: {type(e).__name__}: {e}")
        return np.nan, np.nan, np.nan


if __name__ == "__main__":
    print(f"\n🔍 IV Skew Momentum (Refined) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        skew, call_iv, put_iv = compute_25d_skew(t)
        if not np.isnan(skew):
            results.append({
                'ticker': t,
                'skew_25d': round(skew, 4),
                'call_iv_25d': round(call_iv, 4),
                'put_iv_25d': round(put_iv, 4),
            })
            print(f"  {t}: skew={skew:.4f} (call={call_iv:.4f}, put={put_iv:.4f})")
        else:
            print(f"  {t}: N/A")

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    # Save snapshot for time-series accumulation
    os.makedirs("data", exist_ok=True)
    snapshot_path = "data/iv_skew_momentum_refined_latest.csv"
    df['date'] = datetime.now().strftime("%Y-%m-%d")
    df.to_csv(snapshot_path, index=False)
    print(f"\n✅ Saved to {snapshot_path}")

    # Also append to historical snapshots
    hist_path = "data/snapshots/iv_skew_momentum_refined.csv"
    os.makedirs("data/snapshots", exist_ok=True)
    if os.path.exists(hist_path):
        hist = pd.read_csv(hist_path)
        hist = pd.concat([hist, df], ignore_index=True)
        # Keep unique by (ticker, date)
        hist = hist.drop_duplicates(subset=['ticker', 'date'], keep='last')
    else:
        hist = df.copy()
    hist.to_csv(hist_path, index=False)
    print(f"   Appended to {hist_path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")