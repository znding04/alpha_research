#!/usr/bin/env python3
"""IC Analysis for alpha_49 — VRP Focus (Variance Risk Premium).

Tests whether the VRP signal (IV^2 - RV^2) predicts forward returns
across the 6 focus tickers (AAPL, MSFT, GOOGL, AMZN, SPY, QQQ).

Uses forward 5-day returns AFTER the snapshot date (via signal_as_of,
which anchors to the CSV's max date column or its file mtime).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime

from common.utils import (
    compute_ic,
    forward_return,
    forward_returns_available,
    signal_as_of,
)
from common.universe import FOCUS_TICKERS


def run_ic_analysis():
    """Run IC analysis on VRP Focus signals vs forward returns."""
    print(
        f"\n📈 IC Analysis — VRP Focus — "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    print("=" * 70)

    signal_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "vrp_focus_latest.csv"
    )
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. "
              f"Run alpha_49_vrp_focus/main.py first.")
        return None

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index("ticker")["vrp_variance"]

    print(f"\nVRP Variance (IV^2 - RV^2) signals (snapshot as of {as_of.date()}):")
    print(signals.to_string())

    # Fetch 5-day forward returns AFTER the snapshot date
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in FOCUS_TICKERS:
        ret = forward_return(t, as_of, days=5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    # Align signals and returns on common tickers
    common = signals.index.intersection(returns.index)
    sig_aligned = signals.loc[common]
    ret_aligned = returns.loc[common]

    if len(sig_aligned) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers).")
        return None

    ic = compute_ic(sig_aligned, ret_aligned)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    print(f"  n_obs: {len(sig_aligned)} tickers (single snapshot)")
    print("\nNote: Full rolling IC requires daily signal snapshots accumulated over time.")
    return ic


if __name__ == "__main__":
    run_ic_analysis()