#!/usr/bin/env python3
"""IC Analysis for Alpha 38 — VRP (Variance Risk Premium).

Tests whether the VRP signal predicts forward returns.

Cross-sectional ranking: higher VRP → expensive vol (short/avoid),
                       lower VRP → cheap vol (long/overweight).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime

from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_returns_available, signal_as_of
from common.universe import TICKERS


def run_ic_analysis():
    """Run IC analysis on current VRP signals vs forward returns."""
    print(f"\n📈 IC Analysis — VRP — Alpha 38 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = "data/vrp_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. Run alpha_38_vrp/main.py first.")
        return

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['vrp']

    print("\nVRP signals:")
    print(signals.to_string())

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]

    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers)")
        return

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")

    metrics = compute_signal_metrics(pd.Series([ic], index=['ic']))
    print(f"\n📋 Signal Metrics: {metrics}")

    return ic


def main():
    """Main entry point."""
    return run_ic_analysis()


if __name__ == "__main__":
    main()
