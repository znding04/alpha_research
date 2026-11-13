#!/usr/bin/env python3
"""IC Analysis for Alpha 39 — VRP with EWMA-vol Forecast.

Tests whether the VRP_ewma signal predicts forward returns.

Cross-sectional ranking: higher VRP_ewma → expensive vol (short/avoid),
                       lower VRP_ewma → cheap vol (long/overweight).
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
    """Run IC analysis on current VRP_ewma signals vs forward returns."""
    print(f"\nIC Analysis — VRP EWMA — Alpha 39 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    signal_path = "data/vrp_ewma_latest.csv"
    if not os.path.exists(signal_path):
        print(f"No signal data found at {signal_path}. Run alpha_39_vrp_ewma/main.py first.")
        return

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['vrp']

    print("\nVRP_ewma signals:")
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
    print(f"\nInformation Coefficient (5-day forward): {ic:.4f}")

    metrics = compute_signal_metrics(pd.Series([ic], index=['ic']))
    print(f"\nSignal Metrics: {metrics}")

    return ic


def main():
    """Main entry point."""
    return run_ic_analysis()


if __name__ == "__main__":
    main()
