#!/usr/bin/env python3
"""IC Analysis for IV Rank Percentile signal.

Tests whether IV percentile rank predicts forward returns.
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
from common.utils import compute_ic, compute_signal_metrics, rolling_ic

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_forward_returns(ticker_str, days_ahead=5):
    """Get forward returns for a ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{days_ahead + 10}d")
        if len(hist) < days_ahead + 1:
            return np.nan
        current = hist['Close'].iloc[-days_ahead - 1]
        future = hist['Close'].iloc[-1]
        return (future - current) / current
    except Exception:
        return np.nan


def run_ic_analysis():
    """Run IC analysis on current IV percentile signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Rank Percentile — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest percentile data
    data_path = "data/iv_rank_percentile_latest.csv"
    if not os.path.exists(data_path):
        print(f"❌ No data found at {data_path}. Run main.py first.")
        return
    
    df = pd.read_csv(data_path)
    
    # Get IV percentile per ticker
    iv_pct = df.set_index('ticker')['iv_percentile']
    
    print("\nCurrent IV Percentiles:")
    print(iv_pct.to_string())
    
    # Get forward returns (5-day)
    print("\nFetching 5-day forward returns...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    
    # Align and compute IC
    signals = iv_pct
    returns = pd.Series(forward_returns)
    
    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]
    
    # Drop NaN
    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]
    
    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers with valid percentile)")
        return
    
    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    
    # Interpretation
    if ic > 0.1:
        print("  ✅ Positive IC: High IV percentile → positive forward returns (momentum)")
    elif ic < -0.1:
        print("  ✅ Negative IC: High IV percentile → negative forward returns (mean reversion)")
    else:
        print("  ⚪ Weak IC: No clear predictive signal at this horizon")
    
    # Also test IV z-score
    iv_zscore = df.set_index('ticker')['iv_zscore']
    signals_z = iv_zscore.loc[common][valid]
    
    if signals_z.notna().sum() >= 3:
        ic_z = compute_ic(signals_z, returns)
        print(f"  IV Z-Score IC: {ic_z:.4f}")
    
    print("\nNote: Full rolling IC requires historical percentile snapshots.")
    print("      Run main.py daily to build time series, then analyze.")
    
    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic historical data for demonstration."""
    print("\n🔄 Simulated Rolling IC (demo with random walks):")
    print("-" * 50)
    
    # Generate synthetic signal and return data for demonstration
    np.random.seed(42)
    n_days = 60
    
    # Dates as columns, assets as rows
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')
    
    signals_data = {}
    returns_data = {}
    
    for t in TICKERS:
        # Signal: slow-moving IV percentile (mean-reverting around 50)
        signal = 50 + np.cumsum(np.random.randn(n_days) * 2) + 10 * np.sin(np.arange(n_days) * 0.2)
        signal = np.clip(signal, 0, 100)  # Percentile bounds
        signals_data[t] = signal
        
        # Returns: mean-reverting signal (high IV % → negative returns)
        # IC should be negative if mean reversion works
        returns_data[t] = -signal * 0.0015 + np.random.randn(n_days) * 0.02
    
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
    
    print(f"Rolling IC (20-day window, simulated mean-reversion):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    
    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()