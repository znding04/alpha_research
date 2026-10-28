#!/usr/bin/env python3
"""IC Analysis for IV Skew-Term Structure Signal."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np

from common.utils import compute_ic, rolling_ic, compute_signal_metrics

def run_ic_analysis():
    print("\n📊 IC Analysis — IV Skew-Term Structure Signal")
    print("=" * 60)

    try:
        df_signals = pd.read_csv("data/iv_skew_term_latest.csv")
        print(f"✓ Loaded {len(df_signals)} tickers from snapshot")
    except FileNotFoundError:
        print("✗ No snapshot found — run main.py first")
        return

    print("\n📈 Signal Summary:")
    print(f"  Mean signal_strength: {df_signals['signal_strength'].mean():.4f}")
    print(f"  Std signal_strength: {df_signals['signal_strength'].std():.4f}")
    print(f"  Positive signals (BUY): {(df_signals['signal_strength'] > 0).sum()}")
    print(f"  Negative signals (SELL): {(df_signals['signal_strength'] < 0).sum()}")

    df_sorted = df_signals.sort_values('signal_strength', ascending=False)
    print("\n🏆 Top signals:")
    print(df_sorted[['ticker', 'signal_strength', 'iv_slope', 'skew_slope']].head(5).to_string(index=False))

    print("\n📌 Note: Full historical IC requires accumulated snapshots (multiple dates)")
    print("   and forward return data (e.g., 21-day returns). Use common/history.py")
    print("   and common/utils.py (compute_ic, rolling_ic) for full analysis.")

if __name__ == "__main__":
    run_ic_analysis()
