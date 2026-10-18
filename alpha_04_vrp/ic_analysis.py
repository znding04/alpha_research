#!/usr/bin/env python3
"""IC Analysis for VRP (Variance Risk Premium) signal.

Tests whether VRP metrics predict forward returns.
"""

import os

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_vol_change, forward_returns_available, signal_as_of


from common.universe import TICKERS


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current VRP signals vs forward returns."""
    print(f"\n📈 IC Analysis — VRP (Variance Risk Premium) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest VRP data
    vrp_path = "data/vrp_latest.csv"
    if not os.path.exists(vrp_path):
        print(f"❌ No VRP data found at {vrp_path}. Run main.py first.")
        return
    
    vrp_df = pd.read_csv(vrp_path)
    as_of = signal_as_of(vrp_path)
    
    # Get VRP variance signal per ticker
    vrp_signal = vrp_df.set_index('ticker')['vrp_variance']
    
    print("\nVRP (IV² - RV²) by ticker:")
    print(vrp_signal.to_string())
    
    # Get forward returns (5-day)
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    
    # Align and compute IC
    signals = vrp_signal
    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None
    
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
    
    # Also test VRP ratio signal
    vrp_ratio = vrp_df.set_index('ticker')['vrp_ratio']
    signals2 = vrp_ratio.loc[common]
    valid2 = signals2.notna() & returns.notna()
    if len(signals2[valid2]) >= 3:
        ic2 = compute_ic(signals2[valid2], returns[valid2])
        print(f"   VRP Ratio IC: {ic2:.4f}")
    
    # Test ATM IV level signal
    atm_iv = vrp_df.set_index('ticker')['atm_iv']
    signals3 = atm_iv.loc[common]
    valid3 = signals3.notna() & returns.notna()
    if len(signals3[valid3]) >= 3:
        ic3 = compute_ic(signals3[valid3], returns[valid3])
        print(f"   ATM IV IC: {ic3:.4f}")
    
    if ic > 0.05:
        print("   → Positive IC: Higher VRP (expensive options) predicts positive returns")
    elif ic < -0.05:
        print("   → Negative IC: Higher VRP predicts negative returns")
    else:
        print("   → Near-zero IC: No clear predictive power at this horizon")
    
    print("\nNote: Full rolling IC requires historical VRP snapshots.")
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
        # Signal: VRP (mean-reverting around positive mean ~0.0004)
        signal = 0.0004 + np.cumsum(np.random.randn(n_days) * 0.0001) + 0.0001 * np.sin(np.arange(n_days) * 0.2)
        signals_data[t] = signal
        
        # Returns: positive correlation with VRP (earn the variance risk premium)
        returns_data[t] = signal * 0.8 + np.random.randn(n_days) * 0.012
    
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