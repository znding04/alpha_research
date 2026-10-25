#!/usr/bin/env python3
"""IC Analysis — IV Skew Momentum Refined (alpha_24).

Tests whether 5-day change in 25-delta put-call skew predicts forward returns.
Cross-sectional rank correlation (Spearman) between signal and 5-day forward return.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from datetime import datetime
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_returns_available, signal_as_of
from common.universe import TICKERS

def run_ic_analysis():
    print(f"\n📈 IC Analysis — IV Skew Momentum Refined — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    path = "data/iv_skew_momentum_refined_latest.csv"
    if not os.path.exists(path):
        print(f"❌ No signal at {path}. Run main.py first.")
        return
    df = pd.read_csv(path)
    as_of = signal_as_of(path)
    # Derive change proxy: if only one snapshot, change = 0 (needs history for real Δ)
    signals = df.set_index('ticker')['skew_25d']
    print("\n25Δ Skew (call - put):")
    print(signals.to_string())
    print(f"\nNote: Real 5-day Δ(skew) needs accumulated snapshots (see data/snapshots/).")
    print("   Cross-sectional rank of current skew vs 5-day forward returns:")
    fwd = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        fwd[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    returns = pd.Series(fwd)
    if not forward_returns_available(returns, as_of, 5):
        return None
    common = signals.index.intersection(returns.index)
    s, r = signals.loc[common], returns.loc[common]
    if len(s) < 3:
        print("\n⚠️ Insufficient data (need ≥3 tickers).")
        return
    ic = compute_ic(s, r)
    print(f"\n📊 IC (skew vs 5d fwd return): {ic:.4f}")
    print("   Positive = high call-skew tickers outperform; negative = put-skew outperforms.")
    return ic

if __name__ == "__main__":
    run_ic_analysis()
