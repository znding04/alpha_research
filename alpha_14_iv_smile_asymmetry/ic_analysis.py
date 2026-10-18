#!/usr/bin/env python3
"""IC Analysis for Put/Call OI-Weighted IV Spread signal.

Tests whether put/call positioning (volume/OI weighted IV spreads and ratios)
predicts forward returns.
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
    """Run IC analysis on current positioning signals vs forward returns."""
    print(f"\n📈 IC Analysis — Put/Call OI-Weighted IV Spread — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load latest positioning data
    pos_path = "data/oi_weighted_iv_spread_latest.csv"
    if not os.path.exists(pos_path):
        print(f"❌ No positioning data found at {pos_path}. Run main.py first.")
        return
    
    pos_df = pd.read_csv(pos_path)
    as_of = signal_as_of(pos_path)
    
    print("\nPositioning Signals:")
    for _, row in pos_df.iterrows():
        print(f"  {row['ticker']}: VolRatio={row['vol_ratio']:.4f}, "
              f"VolIVSpread={row['vol_iv_spread']:.6f}, OIIVSpread={row['oi_iv_spread']:.6f}")
    
    # Get forward returns (5-day)
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    
    # Test multiple signals
    signals_to_test = {
        'vol_ratio': pos_df.set_index('ticker')['vol_ratio'],
        'vol_iv_spread': pos_df.set_index('ticker')['vol_iv_spread'],
        'vol_iv_spread_norm': pos_df.set_index('ticker')['vol_iv_spread_norm'],
        'oi_iv_spread': pos_df.set_index('ticker')['oi_iv_spread'],
        'oi_iv_spread_norm': pos_df.set_index('ticker')['oi_iv_spread_norm'],
        'median_iv_spread': pos_df.set_index('ticker')['median_iv_spread'],
    }
    
    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    
    print("\n📊 Information Coefficients (5-day forward):")
    for name, signals in signals_to_test.items():
        common = signals.index.intersection(returns.index)
        sig = signals.loc[common]
        ret = returns.loc[common]
        sig = sig.dropna()
        ret = ret.loc[sig.index]
        
        if len(sig) >= 3:
            ic = compute_ic(sig, ret)
            print(f"  {name:25s}: IC = {ic:.4f} (n={len(sig)})")
        else:
            print(f"  {name:25s}: Insufficient data (n={len(sig)})")
    
    print("\nNote: Full rolling IC requires historical positioning snapshots.")
    print("      Run main.py daily to build time series, then analyze.")


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic historical data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)
    
    np.random.seed(42)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')
    
    signals_data = {}
    returns_data = {}
    
    for t in TICKERS:
        # Signal: put/call vol ratio mean-reverting around 1.0
        # High ratio (put heavy) → hedging → mean reversion UP
        # Low ratio (call heavy) → speculation → pullback DOWN
        signal = 1.0 + np.cumsum(np.random.randn(n_days) * 0.05)
        signal = np.clip(signal, 0.3, 3.0)  # realistic bounds
        signals_data[t] = signal
        
        # Returns: negative correlation with vol ratio (put heavy → bounce)
        returns_data[t] = -signal * 0.15 + np.random.randn(n_days) * 0.02
    
    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS
    
    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)
    
    print(f"Rolling IC (20-day window, simulated put/call vol ratio):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    
    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()