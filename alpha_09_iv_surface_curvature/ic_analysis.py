#!/usr/bin/env python3
"""IC Analysis for IV Surface Curvature signal.

Tests whether smile curvature (butterfly spreads / normalized curvature)
predicts forward returns.
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
    """Run IC analysis on current curvature signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Surface Curvature — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest curvature data
    curv_path = "data/iv_surface_curvature_latest.csv"
    if not os.path.exists(curv_path):
        print(f"❌ No curvature data found at {curv_path}. Run main.py first.")
        return
    
    curv_df = pd.read_csv(curv_path)
    as_of = signal_as_of(curv_path)
    
    # Get curvature signals per ticker
    norm_curv = curv_df.set_index('ticker')['normalized_curvature']
    butterfly = curv_df.set_index('ticker')['butterfly_25d']
    skew = curv_df.set_index('ticker')['skew']
    atm_iv = curv_df.set_index('ticker')['atm_iv']
    
    print("\nNormalized Curvature by ticker:")
    print(norm_curv.to_string())
    
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
    common = norm_curv.index.intersection(returns.index)
    
    # Test 1: Normalized Curvature
    signals = norm_curv.loc[common]
    valid = signals.notna() & returns.notna()
    if len(signals[valid]) >= 3:
        ic = compute_ic(signals[valid], returns[valid])
        print(f"\n📊 Normalized Curvature IC (5-day forward): {ic:.4f}")
        if ic > 0.05:
            print("   → Positive IC: Higher smile curvature predicts positive returns")
        elif ic < -0.05:
            print("   → Negative IC: Higher smile curvature predicts negative returns")
        else:
            print("   → Near-zero IC: No clear predictive power at this horizon")
    else:
        ic = np.nan
        print("\n⚠️ Insufficient data for Normalized Curvature IC")
    
    # Test 2: Butterfly 25d
    signals2 = butterfly.loc[common]
    valid2 = signals2.notna() & returns.notna()
    if len(signals2[valid2]) >= 3:
        ic2 = compute_ic(signals2[valid2], returns[valid2])
        print(f"\n📊 Butterfly 25d IC (5-day forward): {ic2:.4f}")
    else:
        ic2 = np.nan
    
    # Test 3: Skew
    signals3 = skew.loc[common]
    valid3 = signals3.notna() & returns.notna()
    if len(signals3[valid3]) >= 3:
        ic3 = compute_ic(signals3[valid3], returns[valid3])
        print(f"📊 Skew IC (5-day forward): {ic3:.4f}")
    else:
        ic3 = np.nan
    
    # Test 4: ATM IV
    signals4 = atm_iv.loc[common]
    valid4 = signals4.notna() & returns.notna()
    if len(signals4[valid4]) >= 3:
        ic4 = compute_ic(signals4[valid4], returns[valid4])
        print(f"📊 ATM IV IC (5-day forward): {ic4:.4f}")
    else:
        ic4 = np.nan
    
    print("\nNote: Full rolling IC requires historical curvature snapshots.")
    print("      Run main.py daily to build time series, then analyze.")
    
    return {'norm_curvature': ic, 'butterfly': ic2, 'skew': ic3, 'atm_iv': ic4}


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
        # Signal: normalized curvature (mean-reverting around ~0.05)
        # Positive skew: curvature tends to spike during stress
        base_curv = 0.05 + 0.02 * np.sin(np.arange(n_days) * 0.1)
        noise = np.cumsum(np.random.randn(n_days) * 0.005)
        signal = np.maximum(base_curv + noise, 0.01)  # curvature always positive
        signals_data[t] = signal
        
        # Returns: slight negative correlation with curvature
        # High curvature = fear/stress = potential mean reversion bounce (positive return)
        # But also could signal crash risk (negative return)
        # Let's assume slight positive: high curvature → bounce
        returns_data[t] = signal * 0.5 + np.random.randn(n_days) * 0.012
    
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