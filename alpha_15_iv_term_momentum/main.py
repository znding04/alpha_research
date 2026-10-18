#!/usr/bin/env python3
"""IV Term Structure Momentum alpha signal.

Tracks the rate of change (momentum) of the IV term structure slope.
Signal = d(term_slope)/dt — captures acceleration/deceleration of 
IV curve steepening/flattening as a regime change indicator.

- Positive momentum: term structure steepening (far IV rising faster than near IV)
  → Normalizing regime, complacency returning
- Negative momentum: term structure flattening/inverting (near IV rising faster)
  → Stress building, fear accelerating
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
import json

from common.universe import TICKERS
HISTORY_FILE = "data/iv_term_momentum_history.json"
LOOKBACK_DAYS = 60  # Keep 60 days of history for momentum calc


def compute_atm_iv(chain_df, current_price):
    """Compute ATM IV for a given option chain."""
    if len(chain_df) == 0:
        return np.nan
    idx = (chain_df['strike'] - current_price).abs().idxmin()
    row = chain_df.loc[idx]
    iv = row['impliedVolatility']
    return iv if pd.notna(iv) and iv > 0.01 else np.nan


def compute_term_structure_snapshot(ticker_str):
    """Compute current term structure slope for a single ticker (one snapshot)."""
    try:
        tq = yf.Ticker(ticker_str)

        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            return None

        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append((d, (d - now).days))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if len(valid_exps) < 2:
            return None

        results = []
        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                calls = chain.calls
                puts = chain.puts

                calls = calls[
                    (calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)
                ].copy()
                puts = puts[
                    (puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)
                ].copy()

                if len(calls) < 5 or len(puts) < 5:
                    continue

                call_atm_iv = compute_atm_iv(calls, current_price)
                put_atm_iv = compute_atm_iv(puts, current_price)

                if pd.isna(call_atm_iv) and pd.isna(put_atm_iv):
                    continue

                atm_ivs = [iv for iv in [call_atm_iv, put_atm_iv] if not pd.isna(iv)]
                atm_iv = np.mean(atm_ivs)

                results.append({
                    'expiration': exp_str,
                    'dte': dte,
                    'atm_iv': atm_iv,
                })
            except Exception:
                continue

        if len(results) < 2:
            return None

        df = pd.DataFrame(results)
        df = df.sort_values('dte')

        near_iv = df.iloc[0]['atm_iv']
        far_iv = df.iloc[-1]['atm_iv']
        near_dte = df.iloc[0]['dte']
        far_dte = df.iloc[-1]['dte']

        term_slope = (far_iv - near_iv) / (far_dte - near_dte) if far_dte != near_dte else np.nan

        return {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'near_atm_iv': round(near_iv, 4),
            'far_atm_iv': round(far_iv, 4),
            'near_dte': int(near_dte),
            'far_dte': int(far_dte),
            'term_slope': round(term_slope, 6),
            'n_expirations': len(df),
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


def load_history():
    """Load historical term structure snapshots from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_history(history):
    """Save historical term structure snapshots to JSON file."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def compute_momentum(history, ticker, lookback=5):
    """Compute term structure slope momentum over lookback days.
    
    Returns:
        - momentum_1d: 1-day change in term_slope
        - momentum_5d: 5-day change in term_slope
        - momentum_10d: 10-day change in term_slope
        - slope_zscore: z-score of current slope vs lookback window
    """
    if ticker not in history or len(history[ticker]) < lookback + 1:
        return {
            'momentum_1d': np.nan,
            'momentum_5d': np.nan,
            'momentum_10d': np.nan,
            'slope_zscore': np.nan,
            'history_len': len(history.get(ticker, [])),
        }

    # Get recent slopes sorted by date
    entries = sorted(history[ticker], key=lambda x: x['timestamp'])
    slopes = [e['term_slope'] for e in entries if not pd.isna(e['term_slope'])]
    dates = [e['timestamp'] for e in entries if not pd.isna(e['term_slope'])]

    if len(slopes) < lookback + 1:
        return {
            'momentum_1d': np.nan,
            'momentum_5d': np.nan,
            'momentum_10d': np.nan,
            'slope_zscore': np.nan,
            'history_len': len(slopes),
        }

    current_slope = slopes[-1]
    prev_1d = slopes[-2] if len(slopes) > 1 else np.nan
    prev_5d = slopes[-6] if len(slopes) > 5 else np.nan
    prev_10d = slopes[-11] if len(slopes) > 10 else np.nan

    # Recent window for z-score (last 20 days or all available)
    window = slopes[-20:] if len(slopes) >= 20 else slopes
    window_mean = np.mean(window)
    window_std = np.std(window) if len(window) > 1 else np.nan

    momentum_1d = current_slope - prev_1d if not pd.isna(prev_1d) else np.nan
    momentum_5d = current_slope - prev_5d if not pd.isna(prev_5d) else np.nan
    momentum_10d = current_slope - prev_10d if not pd.isna(prev_10d) else np.nan
    slope_zscore = (current_slope - window_mean) / window_std if window_std and window_std > 0 else np.nan

    return {
        'momentum_1d': round(momentum_1d, 8) if not pd.isna(momentum_1d) else np.nan,
        'momentum_5d': round(momentum_5d, 8) if not pd.isna(momentum_5d) else np.nan,
        'momentum_10d': round(momentum_10d, 8) if not pd.isna(momentum_10d) else np.nan,
        'slope_zscore': round(slope_zscore, 4) if not pd.isna(slope_zscore) else np.nan,
        'history_len': len(slopes),
    }


if __name__ == "__main__":
    print(f"\n⚡ IV Term Structure Momentum Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Load history
    history = load_history()

    # Compute current snapshots for all tickers
    current_snapshots = {}
    for t in TICKERS:
        snap = compute_term_structure_snapshot(t)
        if snap:
            current_snapshots[t] = snap
            # Append to history
            if t not in history:
                history[t] = []
            history[t].append(snap)

    # Prune history to LOOKBACK_DAYS
    cutoff = datetime.now() - timedelta(days=LOOKBACK_DAYS)
    for t in history:
        history[t] = [e for e in history[t] if datetime.fromisoformat(e['timestamp']) > cutoff]

    # Save updated history
    save_history(history)

    # Compute momentum for each ticker
    results = []
    for t in TICKERS:
        if t not in current_snapshots:
            continue

        snap = current_snapshots[t]
        momentum = compute_momentum(history, t)

        result = {**snap, **momentum}
        results.append(result)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        mom_1d = r['momentum_1d']
        mom_5d = r['momentum_5d']
        z = r['slope_zscore']
        slope = r['term_slope']

        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  Near ATM IV ({r['near_dte']}d): {r['near_atm_iv']:.4f}")
        print(f"  Far ATM IV  ({r['far_dte']}d):  {r['far_atm_iv']:.4f}")
        print(f"  Term slope (per day): {slope:.6f}")
        print(f"  Momentum 1d:   {mom_1d:.8f}" if not pd.isna(mom_1d) else "  Momentum 1d:   N/A")
        print(f"  Momentum 5d:   {mom_5d:.8f}" if not pd.isna(mom_5d) else "  Momentum 5d:   N/A")
        print(f"  Slope z-score: {z:.4f}" if not pd.isna(z) else "  Slope z-score: N/A")
        print(f"  History:       {r['history_len']} days")

        # Interpretation
        if pd.isna(mom_5d):
            print("  ❓ INSUFFICIENT HISTORY")
        elif mom_5d < -0.0005 and slope < -0.001:
            print("  🔴 ACCELERATING BACKWARDATION — Fear intensifying, near-term IV spike")
        elif mom_5d < -0.0005:
            print("  🟠 FLATTENING TERM STRUCTURE — Stress building")
        elif mom_5d > 0.0005 and slope > 0.001:
            print("  🟢 ACCELERATING CONTANGO — Complacency returning, fear fading")
        elif mom_5d > 0.0005:
            print("  🔵 STEEPENING TERM STRUCTURE — Normalizing regime")
        else:
            print("  ➖ STABLE — Minimal term structure momentum")

    # Save latest snapshot + momentum to CSV
    os.makedirs("data", exist_ok=True)
    path = "data/iv_term_momentum_latest.csv"

    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved latest snapshot to {path}")
    print(f"📜 History saved to {HISTORY_FILE} ({LOOKBACK_DAYS}-day rolling)")
    print(f"   Total cost: ~$0.10-0.30 per run\n")