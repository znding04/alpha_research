#!/usr/bin/env python3
"""IC Analysis for Alpha 17 — IV Rank Percentile.

Tests whether the IV percentile signal (current IV vs 1-year history) predicts
forward returns.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, signal_as_of, forward_returns_available
from common.universe import TICKERS


def run_ic_analysis():
    """Run IC analysis on current IV percentile signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Percentile — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = "alpha_17_iv_rank_percentile/data/iv_rank_percentile_latest.csv"
    if not os.path.exists(signal_path):
        # Try absolute path fallback
        if not os.path.exists("data/iv_rank_percentile_latest.csv"):
            print(f"❌ No signal data found at {signal_path}. Run main.py first.")
            return None
        signal_path = "data/iv_rank_percentile_latest.csv"

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['iv_percentile']

    print("\nIV Percentile signals:")
    print(signals.to_string())

    # Fetch 5-day forward returns
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        try:
            # Only compute for tickers present in signals
            ret = forward_return(t, as_of, 5)
            forward_returns[t] = ret
            if t in signals.index:
                print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A (needs 5 trading days)")
        except Exception as e:
            forward_returns[t] = np.nan

    returns = pd.Series(forward_returns)
    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]

    if not forward_returns_available(returns, as_of, 5):
        print("\n⏳ Real IC requires future returns not yet available.")
        return None

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic data for demonstration."""
    print("\n🔄 SYNTHETIC — rolling IC demo (simulated data):")
    print("-" * 50)

    np.random.seed(202)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in TICKERS:
        # Simulated IV percentile signals centered at 50% with random variation
        base_pct = np.random.normal(50, 20, n_days)
        base_pct = np.clip(base_pct, 5, 95)
        # Simulate mean-reversion: high IV% predicts lower future returns
        signals_data[t] = base_pct
        returns_data[t] = (50 - base_pct) * 0.001 + np.random.randn(n_days) * 0.015

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print("Rolling IC (20-day window, simulated):")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")
    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()
