#!/usr/bin/env python3
"""IC Analysis for IV Rank Percentile (1-Year Snapshot History) Alpha Signal.

Computes Information Coefficient (IC) between the IV percentile signal and forward returns.
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

from common.universe import TICKERS
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_vol_change, forward_returns_available, signal_as_of


def run_ic_analysis():
    """Run IC analysis on current IV rank percentile signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Rank Percentile (1Y History) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = "data/iv_rank_percentile_1y_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. Run main.py first.")
        return

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['iv_percentile_1y']
    print(f"IV Percentile signals (as of {as_of.date()}):")
    print(signals.to_string())

    # Fetch forward returns for 5 days
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        forward_returns[t] = ret
        print(f"  {t}: {forward_returns[t]:.4f}" if pd.notna(forward_returns[t]) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        print("⚠️ Forward returns not available yet for 5-day horizon.")
        return None

    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]

    if len(signals) < 3:
        print("⚠️ Insufficient data for IC (need ≥3 tickers).")
        return None

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")

    metrics = compute_signal_metrics(ic)
    print(f"\n📊 Signal Metrics:")
    for k, v in metrics.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")

    return ic


if __name__ == "__main__":
    run_ic_analysis()