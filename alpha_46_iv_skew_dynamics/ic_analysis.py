#!/usr/bin/env python3
"""IC Analysis for Alpha 46 — Cross-Sectional IV Skew (25Δ put-call) Rank.

Forward-return IC: does an extreme-skew cross-section predict forward returns?
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime

from common.universe import TICKERS
from common.utils import compute_ic, forward_return, forward_returns_available, signal_as_of


def run_ic_analysis():
    print(f"\n📈 IC Analysis — Alpha 46 IV Skew — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    signal_path = "data/iv_skew_dynamics_46_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}.")
        return
    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['skew_rank']

    print("\nCross-sectional skew rank (1.0 = extreme put fear):")
    print(signals.to_string())

    forward_returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        forward_returns[t] = ret

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common_t = signals.index.intersection(returns.index)
    s = signals.loc[common_t]
    r = returns.loc[common_t]
    if len(s) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers).")
        return None
    ic = compute_ic(s, r)
    print(f"\n📊 Cross-Sectional Skew-Rank IC (5-day forward): {ic:.4f}")
    return ic


if __name__ == "__main__":
    run_ic_analysis()
