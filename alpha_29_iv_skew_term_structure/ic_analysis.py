#!/usr/bin/env python3
"""IC Analysis for Alpha 29 — IV Skew Term Structure Composite.

Tests the cross-sectional relationship between the IV skew term structure
composite signal and forward returns. The signal captures interaction of:
  - Skew dynamics across expirations (steepening/flattening)
  - IV term structure slope (backwardation vs contango)

Hypothesis: Stress periods (backwardation + steepening skew) predict
negative forward returns.
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
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, signal_as_of, forward_returns_available

from common.universe import TICKERS


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current IV skew term structure composite vs forward returns."""
    print(f"\n📈 IC Analysis — IV Skew Term Structure Composite — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print("Signal = (skew slope per day) * (normalized term slope)")
    print("Hypothesis: Combined stress indicator (backwardation + steepening skew) predicts negative forward returns")

    signal_path = "data/iv_skew_term_structure_latest.csv"
    if not os.path.exists(signal_path):
        print(f"❌ No signal data found at {signal_path}. Run alpha_29/main.py first.")
        return

    df = pd.read_csv(signal_path)
    # Filter out rows with NaN values
    df = df.dropna()

    if len(df) == 0:
        print("❌ No valid signal data after filtering NaNs.")
        return

    as_of = signal_as_of(signal_path)
    signals = df.set_index('ticker')['combined_score']

    print(f"\nCombined composite scores:")
    print(f"  Mean: {signals.mean():.4f} | Std: {signals.std():.4f}")
    print(f"  Min: {signals.min():.4f} | Max: {signals.max():.4f}")
    print(f"  Signal as of: {as_of}")

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    valid_tickers = []
    for t in TICKERS:
        if t in signals.index:
            ret = get_forward_returns(t, 5, as_of)
            forward_returns[t] = ret
            valid_tickers.append(t)
            print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")
        else:
            print(f"  {t}: Not in signal (removed due to missing data)")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    # Intersect with signals
    signals = signals.loc[valid_tickers]
    returns = returns.loc[valid_tickers]

    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]

    if len(signals) < 3:
        print(f"\n⚠️ Insufficient data for IC (need ≥3 tickers, have {len(signals)})")
        return

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    print(f"   Interpretation: {'Positive signal predicts positive returns' if ic > 0 else 'Negative signal predicts positive returns' if ic < 0 else 'No relationship'}")

    # Compute rolling IC (synthetic demonstration)
    print("\nNote: Full rolling IC requires daily signal snapshots accumulated over time.")

    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(102)  # Different seed for variety
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}

    for t in TICKERS[:8]:  # Use fewer for demo
        # More realistic simulation: stress = more negative, calm = positive
        stress_factor = np.random.randn() * 0.05  # Ticker-specific stress level
        signal = np.cumsum(np.random.randn(n_days) * 0.008 + stress_factor)
        signals_data[t] = signal
        returns_data[t] = signal * 0.18 + np.random.randn(n_days) * 0.025

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS[:8]
    returns_df.index = TICKERS[:8]

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print("Rolling IC (20-day window, simulated):")
    print(f"  IC mean: {metrics.get('ic_mean', np.nan):.4f}")
    print(f"  IC std:  {metrics.get('ic_std', np.nan):.4f}")
    print(f"  IR:      {metrics.get('ir', np.nan):.4f}")
    print(f"  Win rate:{metrics.get('win_rate', np.nan):.2%}")

    # Print latest IC values
    print(f"\nLatest 5 rolling IC values:")
    for i, (date, ic_val) in enumerate(ric.iloc[-5:].items()):
        print(f"  {date.strftime('%Y-%m-%d')}: {ic_val:.4f}")

    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()
