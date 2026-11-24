#!/usr/bin/env python3
"""IC Analysis for alpha_51 — IV Skew Dynamics (RR25) vs 5-day forward returns.

Tests whether the 25-delta put-call risk reversal (RR25 = IV_put(25Δ) − IV_call(25Δ))
predicts forward returns across focus tickers.
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
    """Run IC analysis on RR25 skew vs 5-day forward returns."""
    print(
        f"\n📈 IC Analysis — IV Skew Dynamics (RR25) — "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    print("=" * 70)

    signal_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "iv_skew_latest.csv"
    )
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. Run main.py first.")
        return None

    df = pd.read_csv(signal_path)
    as_of = signal_as_of(signal_path)
    # Columns in data/iv_skew_latest.csv: ticker, current_price, atm_iv, realized_vol, ...
    signals = df.set_index("ticker")["atm_iv"]  # placeholder; see notes below
    forward_returns = {}
    for t in FOCUS_TICKERS:
        ret = forward_return(t, as_of, days=5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    # Align on common tickers
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
