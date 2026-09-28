#!/usr/bin/env python3
"""IC Analysis for IV Term Structure Slope signal.

Tests whether term structure slope predicts forward returns.
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
    """Run IC analysis on current term structure signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Term Structure Slope — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest term structure data
    ts_path = "data/iv_term_structure_latest.csv"
    if not os.path.exists(ts_path):
        print(f"❌ No term structure data found at {ts_path}. Run main.py first.")
        return
    
    ts_df = pd.read_csv(ts_path)
    
    # Get term slope per ticker (need to compute from the data)
    # For now, compute slope from near/far IV
    slopes = {}
    for t in TICKERS:
        ticker_data = ts_df[ts_df['ticker'] == t].sort_values('dte')
        if len(ticker_data) >= 2:
            near = ticker_data.iloc[0]
            far = ticker_data.iloc[-1]
            slope = (far['atm_iv'] - near['atm_iv']) / (far['dte'] - near['dte']) if far['dte'] != near['dte'] else np.nan
            slopes[t] = slope
            print(f"  {t}: slope={slope:.6f}, near_iv={near['atm_iv']:.4f} ({near['dte']}d), far_iv={far['atm_iv']:.4f} ({far['dte']}d)")
        else:
            slopes[t] = np.nan
            print(f"  {t}: insufficient data")
    
    # Get forward returns (5-day)
    print("\nFetching 5-day forward returns...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    
    # Align and compute IC
    signals = pd.Series(slopes)
    returns = pd.Series(forward_returns)
    
    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]
    
    # Drop NaN
    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]
    
    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers with valid signals)")
        return
    
    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    
    if ic > 0.05:
        print("   → Positive IC: Steeper contango (rising IV term) predicts positive returns")
    elif ic < -0.05:
        print("   → Negative IC: Backwardation (falling IV term) predicts positive returns (mean reversion)")
    else:
        print("   → Near-zero IC: No clear predictive power at this horizon")
    
    print("\nNote: Full rolling IC requires historical term structure snapshots.")
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
        # Signal: term structure slope (mean-reverting)
        signal = np.cumsum(np.random.randn(n_days) * 0.0001) + 0.0002 * np.sin(np.arange(n_days) * 0.3)
        signals_data[t] = signal
        
        # Returns: negative correlation with slope (backwardation → bounce)
        returns_data[t] = -signal * 0.5 + np.random.randn(n_days) * 0.015
    
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