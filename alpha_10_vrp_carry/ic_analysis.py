#!/usr/bin/env python3
"""IC Analysis for VRP Carry signal.

Tests whether VRP carry/roll-down metrics predict forward returns.
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
    """Run IC analysis on current VRP carry signals vs forward returns."""
    print(f"\n📈 IC Analysis — VRP Carry — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Load latest VRP carry data
    carry_path = "data/vrp_carry_latest.csv"
    if not os.path.exists(carry_path):
        print(f"❌ No VRP carry data found at {carry_path}. Run main.py first.")
        return

    carry_df = pd.read_csv(carry_path)

    # Get near-term VRP carry per ticker (shortest DTE)
    # We need to aggregate by ticker - get the first (nearest) expiration data
    near_data = carry_df.sort_values('dte').groupby('ticker').first()
    
    # Also compute cross-sectional signals from the summary data
    # Load the summary if available, otherwise compute from detailed
    summary_signals = {}
    for t in TICKERS:
        ticker_data = carry_df[carry_df['ticker'] == t].sort_values('dte')
        if len(ticker_data) >= 2:
            near = ticker_data.iloc[0]
            far = ticker_data.iloc[-1]
            near_vrp = near['vrp']
            far_vrp = far['vrp']
            vrp_carry = near_vrp - far_vrp
            dte_diff = far['dte'] - near['dte']
            vrp_slope = (far_vrp - near_vrp) / dte_diff if dte_diff > 0 else np.nan
            roll_down = -vrp_slope
            summary_signals[t] = {
                'vrp_carry': vrp_carry,
                'roll_down_daily': roll_down,
                'carry_ratio': vrp_carry / near_vrp if near_vrp != 0 else np.nan,
                'near_vrp': near_vrp,
            }

    signals_carry = pd.Series({k: v['vrp_carry'] for k, v in summary_signals.items()})
    signals_rolldown = pd.Series({k: v['roll_down_daily'] for k, v in summary_signals.items()})
    signals_carry_ratio = pd.Series({k: v['carry_ratio'] for k, v in summary_signals.items()})

    print("\nVRP Carry Signals:")
    print(signals_carry.to_string())
    print("\nRoll-down/day Signals:")
    print(signals_rolldown.to_string())

    # Get forward returns (5-day)
    print("\nFetching 5-day forward returns...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)

    # Test VRP Carry IC
    common = signals_carry.index.intersection(returns.index)
    if len(common) >= 3:
        ic_carry = compute_ic(signals_carry.loc[common], returns.loc[common])
        ic_rolldown = compute_ic(signals_rolldown.loc[common], returns.loc[common])
        ic_ratio = compute_ic(signals_carry_ratio.loc[common], returns.loc[common])
        
        print(f"\n📊 Information Coefficients (5-day forward):")
        print(f"  VRP Carry IC:       {ic_carry:.4f}")
        print(f"  Roll-down IC:       {ic_rolldown:.4f}")
        print(f"  Carry Ratio IC:     {ic_ratio:.4f}")
    else:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers)")

    print("\nNote: Full rolling IC requires historical VRP carry snapshots.")
    print("      Run main.py daily to build time series, then analyze.")


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
        # Signal: VRP carry with mean-reverting component
        signal = np.cumsum(np.random.randn(n_days) * 0.001) + 0.005 * np.sin(np.arange(n_days) * 0.3)
        signals_data[t] = signal

        # Returns: signal + noise (target IC ~ 0.15-0.25)
        returns_data[t] = signal * 0.4 + np.random.randn(n_days) * 0.015

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

    print(f"Rolling IC (20-day window, simulated VRP carry):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()