#!/usr/bin/env python3
"""IC Analysis for IV Skew Dynamics signal.

Tests whether skew metrics predict forward returns.
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


def fetch_historical_skew(ticker_str, lookback_days=60):
    """Fetch historical skew data by simulating daily snapshots.
    
    Note: yfinance doesn't provide historical option chains easily.
    This is a placeholder for when historical data is available.
    """
    # For now, return current snapshot only
    # In production, you'd store daily snapshots in a database
    pass


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current skew signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Skew Dynamics — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest skew data
    skew_path = "data/iv_skew_latest.csv"
    if not os.path.exists(skew_path):
        print(f"❌ No skew data found at {skew_path}. Run main.py first.")
        return
    
    skew_df = pd.read_csv(skew_path)
    as_of = signal_as_of(skew_path)
    
    # Get near-term skew per ticker (shortest DTE)
    near_skew = skew_df.sort_values('dte').groupby('ticker').first()['skew_25d']
    
    print("\nNear-term 25-delta skew:")
    print(near_skew.to_string())
    
    # Get forward returns (5-day)
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    
    # Align and compute IC
    signals = near_skew
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
    
    # Also test skew term structure slope
    # Get term slope per ticker (need to compute from skew_by_dte)
    # For now just use the first two expirations
    print("\nNote: Full rolling IC requires historical skew snapshots.")
    print("      Run main.py daily to build time series, then analyze.")
    
    return ic


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
        # Signal: slow-moving skew with noise
        signal = np.cumsum(np.random.randn(n_days) * 0.01) + 0.02 * np.sin(np.arange(n_days) * 0.2)
        signals_data[t] = signal
        
        # Returns: signal + noise (IC ~ 0.15-0.20)
        returns_data[t] = signal * 0.3 + np.random.randn(n_days) * 0.02
    
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