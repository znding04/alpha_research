#!/usr/bin/env python3
"""IC Analysis for alpha_30_vrp — Variance Risk Premium signal.

Tests whether VRP metrics predict forward returns over the next 5 days.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

from common.utils import compute_ic, compute_signal_metrics, forward_return, forward_returns_available, signal_as_of
from common.universe import TICKERS


def run_ic_analysis():
    print(f"\n📈 IC Analysis — alpha_30_vrp — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    vrp_path = "data/vrp_alpha_30.csv"
    if not os.path.exists(vrp_path):
        print(f"❌ No VRP data found at {vrp_path}. Run main.py first.")
        return

    vrp_df = pd.read_csv(vrp_path)
    as_of = signal_as_of(vrp_path)

    # Signal: VRP (IV - RV)
    signal = vrp_df.set_index('ticker')['vrp']
    print("\nVRP (ATM IV - realized vol) by ticker:")
    print(signal.to_string())

    # Forward returns
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return

    common = signal.index.intersection(returns.index)
    s = signal.loc[common]
    r = returns.loc[common]
    valid = s.notna() & r.notna()
    s = s[valid]
    r = r[valid]

    if len(s) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers with valid signals)")
        return

    ic = compute_ic(s, r)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    if ic > 0.05:
        print("   → Positive IC: Higher VRP (options expensive vs realized) predicts higher returns")
    elif ic < -0.05:
        print("   → Negative IC: Higher VRP predicts lower returns")
    else:
        print("   → Weak/no IC")


if __name__ == "__main__":
    run_ic_analysis()
