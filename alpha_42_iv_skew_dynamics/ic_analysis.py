#!/usr/bin/env python3
"""IC Analysis for IV Skew Dynamics (25-delta risk reversal)."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, \
    forward_returns_available, signal_as_of

from common.universe import TICKERS

VERSION = 42
VRP_PATH = f"data/iv_skew_dynamics_{VERSION}_latest.csv"


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return 5-day forward return after the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current IV Skew Dynamics signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Skew Dynamics (25δ RR) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    csv_path = VRP_PATH
    if not os.path.exists(csv_path):
        print(f"❌ No IV Skew Dynamics data found at {csv_path}. Run main.py first.")
        return None

    df = pd.read_csv(csv_path)
    as_of = signal_as_of(csv_path)

    # Signal: 25-delta risk reversal RR25
    rr_signal = df.set_index('ticker')['rr_25']
    print("\n25δ Risk Reversal (RR25 = IV_put(25Δ) − IV_call(25Δ)) by ticker:")
    print(rr_signal.to_string())

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common = rr_signal.index.intersection(returns.index)
    signals = rr_signal.loc[common]
    returns_vals = returns.loc[common]

    # Drop NaN
    valid = signals.notna() & returns_vals.notna()
    signals = signals[valid]
    returns_vals = returns_vals[valid]

    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers with valid signals)")
        return None

    ic = compute_ic(signals, returns_vals)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")

    if ic > 0.05:
        print("   → Positive IC: Higher RR (more put skew / fear) predicts positive returns")
    elif ic < -0.05:
        print("   → Negative IC: Higher RR predicts negative returns")
    else:
        print("   → Near-zero IC: No clear predictive power at this horizon")

    # Also test ATM IV level
    atm_iv = df.set_index('ticker')['atm_iv']
    signals3 = atm_iv.loc[common]
    valid3 = signals3.notna() & returns_vals.notna()
    if len(signals3[valid3]) >= 3:
        ic3 = compute_ic(signals3[valid3], returns_vals[valid3])
        print(f"   ATM IV IC: {ic3:.4f}")
        if ic3 > ic:
            print("   → ATM IV level has stronger forward return correlation than skew level")
        elif ic3 < ic:
            print("   → RR25 has stronger forward return correlation than ATM IV level")

    print("\nNote: Full rolling IC requires daily IV Skew Dynamics snapshots.")
    print("      Run main.py daily via cron to build time series, then analyze.")

    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic historical data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(42)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in TICKERS:
        # Signal: RR25 mean-reverting around ~0 (neutral skew), small drift
        rr = 0.00 + np.cumsum(np.random.randn(n_days) * 0.0015) + 0.0001 * np.sin(np.arange(n_days) * 0.15)
        # A tiny negative drift: higher skew (put fear) slightly predicts down returns
        drift = -0.5 * rr
        returns_data[t] = drift + np.random.randn(n_days) * 0.010
        signals_data[t] = rr

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)
    print(f"Rolling IC (20-day window, simulated):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric, metrics


if __name__ == '__main__':
    ic = run_ic_analysis()
    simulate_rolling_ic()