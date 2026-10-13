#!/usr/bin/env python3
"""IC Analysis for VRP Momentum signal.

Tests whether VRP momentum metrics predict forward returns.
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
    """Run IC analysis on current VRP momentum signals vs forward returns."""
    print(f"\n📈 IC Analysis — VRP Momentum — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Load latest VRP momentum data
    vrp_path = "data/vrp_momentum_latest.csv"
    if not os.path.exists(vrp_path):
        print(f"❌ No VRP data found at {vrp_path}. Run main.py first.")
        return

    vrp_df = pd.read_csv(vrp_path)

    # Get near-term VRP and VRP momentum per ticker (shortest DTE)
    near_vrp = vrp_df.sort_values('dte').groupby('ticker').first()['vrp']
    
    # Also compute VRP momentum from the detailed data
    # For each ticker, get the first two expirations and compute difference
    vrp_momentum = {}
    for ticker in TICKERS:
        ticker_data = vrp_df[vrp_df['ticker'] == ticker].sort_values('dte')
        if len(ticker_data) >= 2:
            vrp_momentum[ticker] = ticker_data.iloc[0]['vrp'] - ticker_data.iloc[1]['vrp']
        else:
            vrp_momentum[ticker] = np.nan

    print("\nNear-term VRP:")
    print(near_vrp.to_string())
    print("\nVRP Momentum (near - mid):")
    for t, v in vrp_momentum.items():
        print(f"  {t}: {v:.6f}" if pd.notna(v) else f"  {t}: N/A")

    # Get forward returns (5-day)
    print("\nFetching 5-day forward returns...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    # Test 1: Near VRP vs forward returns
    signals1 = near_vrp
    returns = pd.Series(forward_returns)

    common = signals1.index.intersection(returns.index)
    signals1 = signals1.loc[common]
    returns = returns.loc[common]

    if len(signals1) >= 3:
        ic1 = compute_ic(signals1, returns)
        print(f"\n📊 IC (Near VRP vs 5-day forward): {ic1:.4f}")
    else:
        print("\n⚠️ Insufficient data for Near VRP IC (need ≥3 tickers)")

    # Test 2: VRP Momentum vs forward returns
    signals2 = pd.Series(vrp_momentum)
    common2 = signals2.index.intersection(returns.index)
    signals2 = signals2.loc[common2]
    returns2 = returns.loc[common2]

    if len(signals2) >= 3:
        ic2 = compute_ic(signals2, returns2)
        print(f"📊 IC (VRP Momentum vs 5-day forward): {ic2:.4f}")
    else:
        print("⚠️ Insufficient data for VRP Momentum IC (need ≥3 tickers)")

    # Note about rolling IC
    print("\nNote: Full rolling IC requires historical VRP snapshots.")
    print("      Run main.py daily to build time series, then analyze.")

    return ic1, ic2


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
        # Signal: VRP momentum-like (mean-reverting with noise)
        signal = np.cumsum(np.random.randn(n_days) * 0.005) + 0.01 * np.sin(np.arange(n_days) * 0.3)
        signals_data[t] = signal

        # Returns: negative correlation with VRP momentum (mean reversion)
        returns_data[t] = -signal * 0.2 + np.random.randn(n_days) * 0.015

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