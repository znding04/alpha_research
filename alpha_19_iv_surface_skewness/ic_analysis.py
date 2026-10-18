#!/usr/bin/env python3
"""IC Analysis for IV Surface Skewness signal.

Tests whether smile skewness metrics predict forward returns.
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import sys
sys.path.insert(0, "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_vol_change, forward_returns_available, signal_as_of


TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current skewness signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Surface Skewness — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Load latest skewness data
    skew_path = "data/iv_skewness_latest.csv"
    if not os.path.exists(skew_path):
        print(f"❌ No skewness data found at {skew_path}. Run main.py first.")
        return

    skew_df = pd.read_csv(skew_path)
    as_of = signal_as_of(skew_path)

    # Get key signals per ticker
    signals_dict = {}
    for col in ['iv_skewness', 'iv_kurtosis', 'iv_variance', 'wing_skew']:
        if col in skew_df.columns:
            signals_dict[col] = skew_df.set_index('ticker')[col]
            print(f"\n{col}:")
            print(signals_dict[col].to_string())

    # Get forward returns (5-day)
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    # Align and compute IC for each signal
    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None
    results = {}

    for sig_name, signals in signals_dict.items():
        common = signals.index.intersection(returns.index)
        if len(common) < 3:
            print(f"\n⚠️ Insufficient data for {sig_name} IC (need ≥3 tickers)")
            continue

        sig_aligned = signals.loc[common]
        ret_aligned = returns.loc[common]

        ic = compute_ic(sig_aligned, ret_aligned)
        results[sig_name] = ic
        print(f"\n📊 {sig_name} IC (5-day forward): {ic:.4f}")

    return results


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic historical data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    # Generate synthetic signal and return data for demonstration
    np.random.seed(42)
    n_days = 60

    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in TICKERS:
        # Signal: slow-moving skewness with noise
        signal = np.cumsum(np.random.randn(n_days) * 0.005) + 0.01 * np.sin(np.arange(n_days) * 0.15)
        signals_data[t] = signal

        # Returns: signal + noise (target IC ~ 0.10-0.15)
        returns_data[t] = signal * 0.25 + np.random.randn(n_days) * 0.02

    # Create DataFrames with assets as rows, dates as columns
    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    # Compute rolling IC
    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print(f"Rolling IC (20-day window, simulated):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()