#!/usr/bin/env python3
"""IC Analysis for alpha_31_iv_skew_dynamics — IV Skew Dynamics.

Cross-sectional IC of 25-delta put-call skew vs 5-day forward returns.
Higher (more negative) put-call skew = more fear = potential mean-reversion.
Negative skew change = rising fear = bearish signal; positive change = easing = bullish.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, yfinance as yf
from datetime import datetime
from common.utils import compute_ic, compute_signal_metrics, forward_return, forward_returns_available, signal_as_of
from common.universe import TICKERS

def run_ic_analysis():
    print(f"\n📈 IC Analysis — alpha_31_iv_skew_dynamics — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    path = "data/iv_skew_dynamics_latest.csv"
    if not os.path.exists(path):
        print(f"❌ No skew data at {path}. Run main.py first.")
        return
    df = pd.read_csv(path)
    as_of = signal_as_of(path)
    # Cross-sectional rank: more negative skew = more fear = lower rank (potential long)
    df['signal'] = df['skew_average'].fillna(0)
    signal = df.set_index('ticker')['signal']
    print("\nIV Skew (near+far avg) by ticker:")
    print(signal.to_string())
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    returns = {}
    for t in TICKERS:
        ret = forward_return(t, as_of, 5)
        returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
    s = pd.Series(returns)
    if not forward_returns_available(s, as_of, 5):
        print("Insufficient forward returns."); return
    common = signal.index.intersection(s.index)
    s_sig = signal.loc[common]; s_ret = s.loc[common]
    valid = s_sig.notna() & s_ret.notna()
    if valid.sum() < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers)"); return
    ic = compute_ic(s_sig[valid], s_ret[valid])
    print(f"\n📊 Cross-sectional IC (5-day fwd): {ic:.4f}")
    if ic > 0.05:
        print("   More positive skew (less fear) predicts higher returns")
    elif ic < -0.05:
        print("   More negative skew (more fear) predicts higher returns (mean-reversion)")
    else:
        print("   Weak/no predictive signal")

if __name__ == "__main__":
    run_ic_analysis()
