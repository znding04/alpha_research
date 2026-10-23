#!/usr/bin/env python3
"""IC Analysis — alpha_22 Put-Call Parity Residual.

Tests whether extreme parity residuals predict 5-day forward returns.
High positive residual = put overpriced (hard borrow, short-bias signal);
negative = call overpriced (easy borrow, long-bias). Cross-sectionally,
ranking by |residual| and comparing to next-5-day returns gives a direct IC.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from datetime import datetime
from common.universe import TICKERS
from common.utils import compute_ic, compute_signal_metrics, forward_return, signal_as_of, forward_returns_available

def run_ic():
    path = "data/alpha_22_put_call_parity_latest.csv"
    if not os.path.exists(path):
        print(f"❌ Signal data not at {path}; run main.py first.")
        return None
    df = pd.read_csv(path)
    signals = df.set_index('ticker')['parity_bps'].astype(float)
    as_of = signal_as_of(path)
    # Use absolute residual magnitude as the ranked signal (extreme in either direction predicts)
    signals_mag = signals.abs()
    fwd = {}
    for t in TICKERS:
        fwd[t] = forward_return(t, as_of, 5)
    returns = pd.Series(fwd)
    common = signals_mag.index.intersection(returns.index)
    s = signals_mag.loc[common].dropna()
    r = returns.loc[s.index].dropna()
    if len(s) < 3 or s.empty:
        print("⚠️ Not enough tickers for IC.")
        return None
    ic = compute_ic(s, r)
    print(f"\n📈 IC (5d fwd) — parity |residual| vs returns: {ic:.4f}  (n={len(s)}, as_of={as_of.date()})")
    # Also report IC for signed residual (positive = short-bias, negative = long-bias)
    ic_signed = compute_ic(signals.loc[s.index], r)
    print(f"   Signed residual (positive = short-bias) vs returns: {ic_signed:.4f}")
    return ic

if __name__ == "__main__":
    print(f"\n📈 IC — alpha_22 Put-Call Parity — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    run_ic()
