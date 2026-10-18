#!/usr/bin/env python3
"""IC Analysis for IV Skew Convexity signal.

Tests whether skew convexity metrics predict forward returns.
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
    """Run IC analysis on current convexity signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Skew Convexity — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest convexity data
    convexity_path = "data/iv_skew_convexity_latest.csv"
    if not os.path.exists(convexity_path):
        print(f"❌ No convexity data found at {convexity_path}. Run main.py first.")
        return
    
    convex_df = pd.read_csv(convexity_path)
    as_of = signal_as_of(convexity_path)
    
    print("\nConvexity signals:")
    for _, row in convex_df.iterrows():
        print(f"  {row['ticker']}: convexity_10d={row['skew_convexity_10d']:.6f}, convexity_5d={row['skew_convexity_5d']:.6f}, tail_prem={row['tail_convexity_premium']:.6f}")
    
    # Get forward returns (5-day)
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    
    # Test multiple signal variants
    signals_to_test = {
        'convexity_10d': convex_df.set_index('ticker')['skew_convexity_10d'],
        'convexity_5d': convex_df.set_index('ticker')['skew_convexity_5d'],
        'tail_convexity_premium': convex_df.set_index('ticker')['tail_convexity_premium'],
        'skew_25d': convex_df.set_index('ticker')['skew_25d'],
        'skew_slope': convex_df.set_index('ticker')['skew_slope'],
        'wing_ratio': convex_df.set_index('ticker')['wing_ratio'],
    }
    
    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    
    print("\n📊 Information Coefficients (5-day forward):")
    for name, signals in signals_to_test.items():
        common = signals.index.intersection(returns.index)
        if len(common) < 3:
            print(f"  {name}: insufficient data")
            continue
        sig_aligned = signals.loc[common]
        ret_aligned = returns.loc[common]
        ic = compute_ic(sig_aligned, ret_aligned)
        print(f"  {name}: IC = {ic:.4f}")
    
    print("\nNote: Full rolling IC requires historical convexity snapshots.")
    print("      Run main.py daily to build time series, then analyze.")


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic historical data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)
    
    # Generate synthetic signal and return data for demonstration
    np.random.seed(42)
    n_days = 60
    
    # Dates as columns, assets as rows
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')
    
    signals_data = {}
    returns_data = {}
    
    for t in TICKERS:
        # Signal: slow-moving convexity with regime shifts
        signal = np.cumsum(np.random.randn(n_days) * 0.005) + 0.01 * np.sin(np.arange(n_days) * 0.15)
        signals_data[t] = signal
        
        # Returns: negative relationship with convexity (high convexity = tail risk priced = mean reversion up)
        # IC ~ -0.15 to -0.20
        returns_data[t] = signal * -0.25 + np.random.randn(n_days) * 0.015
    
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
    
    print(f"Rolling IC (20-day window, simulated, convexity_10d signal):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    
    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()