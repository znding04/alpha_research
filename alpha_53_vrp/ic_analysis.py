#!/usr/bin/env python3
"""IC Analysis for VRP (IV² − RV²) signal — alpha_53.

Tests whether VRP levels predict forward returns.
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
from common.universe import FOCUS_TICKERS

VRP_PATH = "data/vrp53_latest.csv"


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current VRP signals vs forward returns."""
    print(f"\n📈 IC Analysis — VRP — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = "data/vrp53_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No VRP data found at {signal_path}. Run alpha_53_vrp/main.py first.")
        return None

    vrp_df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)

    # Signal: VRP variance (IV² − RV²)
    vrp_signal = vrp_df.set_index('ticker')['vrp_variance']

    print(f"\nVRP (IV² − RV²) by ticker:")
    print(vrp_df.to_string(index=False))

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in FOCUS_TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common = vrp_signal.index.intersection(returns.index)
    signals = vrp_signal.loc[common]
    returns = returns.loc[common]

    # Drop NaN
    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]

    if len(signals) < 3:
        print("\\n⚠️ Insufficient data for IC (need ≥3 tickers with valid signals)")
        return None

    ic = compute_ic(signals, returns)
    print(f"\\n📊 Information Coefficient (5-day forward): {ic:.4f}")

    # Also test VRP ratio and ATM IV level
    if 'vrp_ratio' in vrp_df.columns:
        vrp_ratio = vrp_df.set_index('ticker')['vrp_ratio']
        signals2 = vrp_ratio.loc[common]
        valid2 = signals2.notna() & returns.notna()
        if len(signals2[valid2]) >= 3:
            ic2 = compute_ic(signals2[valid2], returns[valid2])
            print(f"   VRP Ratio IC: {ic2:.4f}")

    if 'atm_iv' in vrp_df.columns:
        atm_iv = vrp_df.set_index('ticker')['atm_iv']
        signals3 = atm_iv.loc[common]
        valid3 = signals3.notna() & returns.notna()
        if len(signals3[valid3]) >= 2:
            ic3 = compute_ic(signals3[valid3], returns[valid3])
            print(f"   ATM IV IC: {ic3:.4f}")

    if ic > 0.05:
        print("   → Positive IC: Higher VRP (expensive options) predicts positive returns")
    elif ic < -0.05:
        print("   → Negative IC: Higher VRP predicts negative returns")
    else:
        print("   → Near-zero IC: No clear predictive power at this horizon")

    print("\\nNote: Full rolling IC requires daily VRP snapshots. This is a single-snapshot analysis.")
    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic data for demonstration."""
    print("🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(101)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in FOCUS_TICKERS:
        # Signal: VRP (mean-reverting around positive mean ~0.0004)
        signal = 0.0004 + np.cumsum(np.random.randn(n_days) * 0.0001) + 0.0001 * np.sin(np.arange(n_days) * 0.2)
        signals_data[t] = signal
        # Returns: positive correlation with VRP (earn the variance risk premium)
        returns_data[t] = signal * 0.8 + np.random.randn(n_days) * 0.012

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = FOCUS_TICKERS
    returns_df.index = FOCUS_TICKERS

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print("Rolling IC (20-day window, simulated):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")

    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()