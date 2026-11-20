#!/usr/bin/env python3
"""IC Analysis for VRP (Variance Risk Premium) — alpha_47."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
from datetime import datetime
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_returns_available, signal_as_of
from common.universe import TICKERS

def run_ic_analysis():
    print(f"\n📈 IC Analysis — VRP — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    path = "data/vrp_latest.csv"
    if not os.path.exists(path):
        print(f"❌ No data at {path}. Run main.py first.")
        return
    vrp_df = pd.read_csv(path)
    as_of = signal_as_of(path)
    vrp_signal = vrp_df.set_index('ticker')['vrp_variance']
    print(f"\nVRP (IV² - RV²) as of {as_of.date()}:")
    print(vrp_signal.to_string())
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return
    common = vrp_signal.index.intersection(returns.index)
    signals = vrp_signal.loc[common]
    returns = returns.loc[common]
    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]
    if len(signals) < 3:
        print(f"\n⚠️ Insufficient data for IC ({len(signals)} < 3)")
        return
    ic = compute_ic(signals, returns)
    print(f"\n📊 VRP IC (5-day forward): {ic:.4f}")
    # Also test VRP ratio
    ratio = vrp_df.set_index('ticker')['vrp_ratio'].loc[common]
    valid2 = ratio.notna() & returns.notna()
    if valid2.sum() >= 3:
        ic2 = compute_ic(ratio[valid2], returns[valid2])
        print(f"   VRP Ratio IC: {ic2:.4f}")
    # ATM IV signal
    atm = vrp_df.set_index('ticker')['atm_iv'].loc[common]
    valid3 = atm.notna() & returns.notna()
    if valid3.sum() >= 3:
        ic3 = compute_ic(atm[valid3], returns[valid3])
        print(f"   ATM IV IC: {ic3:.4f}")

if __name__ == "__main__":
    run_ic_analysis()