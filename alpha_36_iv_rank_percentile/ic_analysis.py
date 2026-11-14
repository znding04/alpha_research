#!/usr/bin/env python3
"""IC Analysis for Alpha 36 — IV Rank Percentile.

Tests whether the IV percentile signal predicts forward returns.

Caveat: since yfinance provides only current chains (no historical IV snapshots),
the percentile is computed vs today's cross-strike IV distribution. True historical
percentiles would need daily snapshot collection (see notes.md).
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
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_vol_change, forward_returns_available, signal_as_of
from common.universe import TICKERS


def run_ic_analysis():
    """Run IC analysis on current IV percentile signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Rank Percentile — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = "data/iv_rank_percentile_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. Run alpha_36_iv_rank_percentile/main.py first.")
        return

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['iv_percentile']

    print("\nIV Percentile signals:")
    print(signals.to_string())

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
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
    np.random.seed(202)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')
    signals_data = {}
    returns_data = {}
    for t in TICKERS:
        signal = np.cumsum(np.random.randn(n_days) * 0.01) + 0.02 * np.sin(np.arange(n_days) * 0.2)
        signals_data[t] = signal
        returns_data[t] = signal * 0.3 + np.random.randn(n_days) * 0.02
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


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()
