#!/usr/bin/env python3
"""IC analysis for IV Term Structure Slope (Refined) signal."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime

from common.utils import compute_ic, rolling_ic, compute_signal_metrics


def load_latest_signal():
    """Load latest signal data."""
    path = "data/iv_term_refined_latest.csv"
    if os.path.exists(path):
        return pd.read_csv(path, index_col='ticker')
    return None


def run_ic_analysis():
    """Run IC analysis on the term structure slope signal."""
    signal_df = load_latest_signal()
    if signal_df is None:
        print("❌ No signal data found. Run main.py first.")
        return None

    print("\n📊 IC Analysis — IV Term Structure Slope (Refined)")
    print("=" * 50)

    # Single-day cross-sectional IC
    # In real usage, would pair with forward returns from same day
    # For now, demonstrate the IC computation framework

    signal = signal_df['slope_norm_pct']

    # Simulate forward returns for demonstration
    # In practice, load from data/forward_returns/ or compute from price data
    np.random.seed(42)
    simulated_returns = pd.Series(
        np.random.randn(len(signal)) * 0.01,  # ~1% daily vol
        index=signal.index
    )

    ic = compute_ic(signal, simulated_returns)
    print(f"\n📈 Single-day IC (simulated returns):")
    print(f"   IC = {ic:.4f}")
    print(f"   This is a placeholder; real IC requires forward return data.")

    # Signal distribution
    print(f"\n📊 Signal Distribution:")
    print(f"   Mean slope: {signal.mean():.2f}%")
    print(f"   Std slope: {signal.std():.2f}%")
    print(f"   Min: {signal.min():.2f}%")
    print(f"   Max: {signal.max():.2f}%")

    # Backwardation tickers (negative slope = stress = mean-reversion long signal)
    backwardation = signal[signal < 0].sort_values()
    contango = signal[signal > 0].sort_values(ascending=False)

    print(f"\n📋 Cross-sectional Ranking:")
    if len(contango) > 0:
        print(f"   Most complacent (positive slope):")
        for t in contango.head(5).index:
            print(f"      {t}: {signal[t]:.2f}%")
    if len(backwardation) > 0:
        print(f"   Most stressed (negative slope = beta signal):")
        for t in backwardation.tail(5).index:
            print(f"      {t}: {signal[t]:.2f}%")
    else:
        print("   No tickers in backwardation (all slopes = 0 due to yfinance defaults)")

    # Save IC results
    results = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'ic_simulated': float(ic) if not np.isnan(ic) else None,
        'signal_mean': float(signal.mean()),
        'signal_std': float(signal.std()),
        'n_tickers': int(len(signal)),
    }

    with open('data/iv_term_refined_ic.txt', 'w') as f:
        f.write(f"IC Analysis — {results['date']}\n")
        f.write(f"IC (simulated): {results['ic_simulated']}\n")
        f.write(f"Signal mean: {results['signal_mean']:.2f}%\n")
        f.write(f"Signal std: {results['signal_std']:.2f}%\n")
        f.write(f"N tickers: {results['n_tickers']}\n")

    print(f"\n✅ IC results saved to data/iv_term_refined_ic.txt")
    return results


if __name__ == "__main__":
    run_ic_analysis()