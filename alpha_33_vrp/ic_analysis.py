#!/usr/bin/env python3
"""IC Analysis for alpha_33_vrp — cross-sectional VRP vs forward returns.

Signal: cross-sectionally ranked VRP variance (IV² − RV²).
Hypothesis: higher VRP (options expensive vs realized) predicts higher forward
equity returns cross-sectionally (volatility risk premium pays out).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime

from common.utils import compute_ic, forward_return, forward_returns_available, signal_as_of

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]

SIGNAL_PATH = "data/vrp_alpha_33_latest.csv"


def run_ic_analysis():
    print(f"\n📈 IC Analysis — alpha_33_vrp — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    if not os.path.exists(SIGNAL_PATH):
        print(f"❌ No signal data at {SIGNAL_PATH}. Run main.py first.")
        return

    df = pd.read_csv(SIGNAL_PATH)
    as_of = signal_as_of(SIGNAL_PATH)

    # Cross-sectional signal: VRP variance (higher = richer options)
    signal = df.set_index('ticker')['vrp_variance']
    print("\nVRP variance (IV² − RV²) by ticker:")
    print(signal.to_string())

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    s_ret = pd.Series(returns)
    if not forward_returns_available(s_ret, as_of, 5):
        print("⚠️ Insufficient forward returns for IC (need ≥1 obs; real IC needs pooled snapshots).")
        return

    common = signal.index.intersection(s_ret.index)
    s_sig = signal.loc[common]
    s_ret = s_ret.loc[common]
    valid = s_sig.notna() & s_ret.notna()
    if valid.sum() < 2:
        print("\n⚠️ Insufficient valid pairs for IC.")
        return

    ic = compute_ic(s_sig[valid], s_ret[valid])
    print(f"\n📊 Cross-sectional IC (5-day forward): {ic:.4f}")
    if ic > 0.05:
        print("   Higher VRP predicts higher forward returns (VRP pays out) ✅")
    elif ic < -0.05:
        print("   Higher VRP predicts lower forward returns ❌")
    else:
        print("   Weak / no predictive signal")

    return ic


if __name__ == "__main__":
    run_ic_analysis()
