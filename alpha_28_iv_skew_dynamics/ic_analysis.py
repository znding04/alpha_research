#!/usr/bin/env python3
"""IC Analysis for Alpha 28 — IV Skew Dynamics.

Tests whether the 25-delta put-call skew predicts forward returns.
"""

import os
import sys
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_returns_available, signal_as_of
from common.universe import TICKERS


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date."""
    return forward_return(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current IV skew signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Skew Dynamics — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = "data/iv_skew_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. Run alpha_28_iv_skew_dynamics/main.py first.")
        return

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    
    # Get near-term skew per ticker (first row per ticker = nearest expiration)
    near_skew = df.groupby('ticker').first()['skew_25d']
    
    print("\nNear-term Skew (25d put - call) signals:")
    print(near_skew.to_string())

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common = near_skew.index.intersection(returns.index)
    signals = near_skew.loc[common]
    returns = returns.loc[common]

    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers)")
        return

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    print("\nNote: Full rolling IC requires daily signal snapshots.")
    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(101)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in TICKERS:
        signal = np.cumsum(np.random.randn(n_days) * 0.005) + np.random.randn(n_days) * 0.01
        signals_data[t] = signal
        returns_data[t] = signal * 0.25 + np.random.randn(n_days) * 0.02

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print("Rolling IC (20-day window, simulated):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()