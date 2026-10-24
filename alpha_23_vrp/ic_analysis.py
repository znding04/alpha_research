#!/usr/bin/env python3
"""IC Analysis for Alpha 23 — VRP (IV^2 - RV^2).

Tests whether the VRP signal predicts forward equity returns across the
cross-section of tickers. Uses the shared IC pipeline from common/utils.py.

Key question: does a high VRP (options expensive relative to realized vol)
predict future 5-day returns at the ticker level?
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

from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, signal_as_of
from common.universe import TICKERS


def compute_vrp_for_ticker(ticker_str) -> float:
    """Extract the VRP value for a single ticker from the latest CSV."""
    signal_path = "data/vrp23_latest.csv"
    if not os.path.exists(signal_path):
        return np.nan
    df = pd.read_csv(signal_path)
    row = df[df['ticker'] == ticker_str]
    if len(row) == 0:
        return np.nan
    vrp = row['vrp'].values[0]
    return float(vrp) if not pd.isna(vrp) else np.nan


def run_vrp_ic_analysis() -> float | None:
    """Run IC analysis on current VRP signals vs forward returns."""
    signal_path = "data/vrp23_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. Run alpha_23_vrp/main.py first.")
        return None

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['vrp']

    print(f"\n📊 VRP IC Analysis — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    print(f"\nVRP (IV^2 - RV^2) signals:")
    print(signals.to_string())

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)

    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]

    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers)")
        return None

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    print("   (positive IC = high VRP → higher future returns)")
    print("   (negative IC = high VRP → lower future returns)")

    metrics = compute_signal_metrics(ic_series=pd.Series([ic]))
    if 'ic_mean' in metrics:
        print(f"   IR (IC / std): {metrics.get('ir', np.nan):.4f}")
        print(f"   Win rate: {metrics.get('win_rate', np.nan):.2%}")
        print(f"   n_obs: {metrics.get('n_obs', 0)}")

    return ic


def simulate_rolling_vrp_ic() -> tuple:
    """Simulate rolling VRP IC with synthetic data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling VRP IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(101)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in TICKERS:
        # Simulate VRP signal: mean-reverting process
        signal = np.cumsum(np.random.randn(n_days) * 0.01) + 0.02
        signals_data[t] = signal
        # Forward returns: weak negative VRP → higher future returns (regression)
        returns_data[t] = -signal * 0.30 + np.random.randn(n_days) * 0.02

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print("Rolling VRP IC (20-day window, simulated):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric, metrics


if __name__ == "__main__":
    run_vrp_ic_analysis()
    simulate_rolling_vrp_ic()