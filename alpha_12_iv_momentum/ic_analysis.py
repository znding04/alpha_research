#!/usr/bin/env python3
"""IC Analysis for IV Momentum signal.

Tests whether IV momentum (short-term IV trend) predicts forward returns.
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
LOOKBACK_DAYS = 5
HISTORY_FILE = "data/iv_momentum_history.json"


def load_history():
    """Load IV history from JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}


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


def build_signal_series_from_history(history, lookback=LOOKBACK_DAYS):
    """Build signal and return series from historical data for IC analysis.
    
    Returns:
        signals_df: DataFrame with assets as rows, dates as columns (momentum values)
        returns_df: DataFrame with assets as rows, dates as columns (forward returns)
    """
    import json
    
    # Group history by date
    daily_data = {}
    for ticker, entries in history.items():
        for entry in entries:
            date = entry['date']
            if date not in daily_data:
                daily_data[date] = {}
            daily_data[date][ticker] = entry['atm_iv']
    
    # Sort dates
    sorted_dates = sorted(daily_data.keys())
    
    # Need at least lookback+1 days to compute momentum
    if len(sorted_dates) < lookback + 1:
        return None, None
    
    # Compute momentum for each date (except first lookback days)
    signals = {}
    returns = {}
    
    for i in range(lookback, len(sorted_dates)):
        date = sorted_dates[i]
        past_date = sorted_dates[i - lookback]
        
        # Get IV values for this date and past date
        iv_now = daily_data[date]
        iv_past = daily_data[past_date]
        
        # Compute momentum for each ticker
        for ticker in TICKERS:
            if ticker in iv_now and ticker in iv_past:
                iv_n = iv_now[ticker]
                iv_p = iv_past[ticker]
                if iv_p > 0:
                    momentum = (iv_n - iv_p) / iv_p  # percent change
                    if ticker not in signals:
                        signals[ticker] = {}
                    signals[ticker][date] = momentum
        
        # Get forward returns for this date (this is a simplification - in practice
        # you'd need to store forward returns at the time of signal generation)
        # For now, we'll skip actual forward returns and note this limitation
    
    return signals, returns


def run_ic_analysis():
    """Run IC analysis on IV momentum signals vs forward returns."""
    import json
    
    print(f"\n📈 IC Analysis — IV Momentum — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest momentum data
    momentum_path = "data/iv_momentum_latest.csv"
    if not os.path.exists(momentum_path):
        print(f"❌ No momentum data found at {momentum_path}. Run main.py first.")
        return
    
    momentum_df = pd.read_csv(momentum_path)
    
    # Get momentum_pct per ticker
    momentum_signals = momentum_df.set_index('ticker')['momentum_pct']
    
    print("\nCurrent IV Momentum (5-day % change):")
    print(momentum_signals.to_string())
    
    # Get forward returns (5-day)
    print("\nFetching 5-day forward returns...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    
    # Align and compute IC
    signals = momentum_signals
    returns = pd.Series(forward_returns)
    
    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]
    
    # Filter out NaN signals
    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]
    
    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers with valid momentum)")
        return
    
    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    
    # Note about historical analysis
    print("\nNote: Full rolling IC requires historical momentum snapshots.")
    print("      Run main.py daily via cron to build time series, then analyze.")
    print("      Current history file stores daily ATM IV for momentum computation.")
    
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
        # Signal: slow-moving IV momentum with mean reversion
        signal = np.cumsum(np.random.randn(n_days) * 0.02) + 0.05 * np.sin(np.arange(n_days) * 0.3)
        signals_data[t] = signal
        
        # Returns: negative correlation with IV momentum (rising IV → downside)
        # IV momentum up (fear) → short-term downside → negative forward returns
        returns_data[t] = -signal * 0.3 + np.random.randn(n_days) * 0.02
    
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
    import json
    run_ic_analysis()
    simulate_rolling_ic()