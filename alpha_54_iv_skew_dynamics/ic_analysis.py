#!/usr/bin/env python3
"""IC Analysis for IV Skew Dynamics (alpha_54)."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime

from common.utils import (
    compute_ic, compute_signal_metrics, rolling_ic,
    forward_return, forward_returns_available, signal_as_of,
)
from common.universe import FOCUS_TICKERS

OUTPUT_PATH = "data/iv_skew_54_latest.csv"
HISTORY_PATH = "data/iv_skew_54_history.json"


def run_ic_analysis():
    """Run single-snapshot IC analysis on current skew signals vs 5-day forward returns."""
    print(f"\n📈 IC Analysis — IV Skew Dynamics (alpha_54) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = OUTPUT_PATH
    if not os.path.exists(signal_path):
        print(f"❌ No skew data found at {signal_path}. Run alpha_54_iv_skew_dynamics/main.py first.")
        return None

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)

    # Skew signal: skew (put IV − call IV)
    skew_signal = df.set_index('ticker')['skew']
    print(f"\nIV Skew (put IV − call IV) by ticker:")
    print(df[['ticker', 'skew']].to_string(index=False))

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in FOCUS_TICKERS:
        ret = forward_return(t, as_of, days=5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common = skew_signal.index.intersection(returns.index)
    signals = skew_signal.loc[common]
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

    if ic > 0.05:
        print("   → Positive IC: Higher skew (put-rich) predicts positive forward returns")
    elif ic < -0.05:
        print("   → Negative IC: Higher skew predicts negative forward returns")
    else:
        print("   → Near-zero IC: No clear predictive power at this horizon")

    print(f"\\nNote: Full rolling IC requires daily signal snapshots pooled over time.")
    print(f"      This is a single-snapshot analysis ({as_of.date()}).")
    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic data for demonstration."""
    print("\\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(101)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in FOCUS_TICKERS:
        # Signal: skew mean-reverting around 0 (positive = fear, negative = complacency)
        signal = np.cumsum(np.random.randn(n_days) * 0.0001) * 0.01
        signals_data[t] = signal
        # Returns: slight negative skew IC (higher skew slightly predicts lower returns,
        # consistent with risk-off premium); noise dominates
        returns_data[t] = -signal * 0.3 + np.random.randn(n_days) * 0.012

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
    ic = run_ic_analysis()
    simulate_rolling_ic()
    if ic is not None:
        print(f"\\nSingle-snapshot IC: {ic:.4f}")
    else:
        print("\\nSingle-snapshot IC: N/A (need forward returns data to be available)")