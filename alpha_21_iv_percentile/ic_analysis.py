#!/usr/bin/env python3
"""IC Analysis for IV Rank Percentile signal (alpha_21).

Tests whether IV percentile rank predicts forward equity returns.
"""
import os
import warnings
warnings.filterwarnings('ignore')

import sys
sys.path.insert(0, "/Users/znding04/Work/alpha_research")

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from common.utils import compute_ic, compute_signal_metrics, rolling_ic

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "iv_percentile_latest.csv")


def get_forward_returns(ticker_str, days_ahead=5):
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{days_ahead + 10}d")
        if len(hist) < days_ahead + 1:
            return np.nan
        current = float(hist['Close'].iloc[-(days_ahead + 1)])
        future = float(hist['Close'].iloc[-1])
        return (future - current) / current
    except Exception:
        return np.nan


def run_ic_analysis():
    print(f"\n📈 IC Analysis — IV Rank Percentile (alpha_21) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    if not os.path.exists(DATA_PATH):
        print(f"❌ No data found at {DATA_PATH}. Run main.py first.")
        return

    df = pd.read_csv(DATA_PATH)
    iv_pct = df.set_index('ticker')['iv_percentile']

    print("\nCurrent IV Percentiles:")
    print(iv_pct.to_string())

    print("\nFetching 5-day forward returns...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    signals = iv_pct
    returns = pd.Series(forward_returns)
    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]
    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]

    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers with valid percentile)")
        return

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")

    if ic > 0.1:
        print("  ✅ Positive IC: High IV percentile → positive forward returns (momentum)")
    elif ic < -0.1:
        print("  ✅ Negative IC: High IV percentile → negative forward returns (mean reversion)")
    else:
        print("  ⚪ Weak IC: No clear predictive signal at this horizon")

    iv_zscore = df.set_index('ticker')['iv_zscore']
    signals_z = iv_zscore.loc[common][valid]
    if signals_z.notna().sum() >= 3:
        ic_z = compute_ic(signals_z, returns)
        print(f"  IV Z-Score IC: {ic_z:.4f}")

    print("\nNote: Full rolling IC requires historical percentile snapshots.")
    print("      Run main.py daily to build time series, then analyze.")

    return ic


def simulate_rolling_ic():
    print("\n🔄 Simulated Rolling IC (demo with mean-reverting signal):")
    print("-" * 50)
    np.random.seed(42)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}
    for t in TICKERS:
        signal = 50 + np.cumsum(np.random.randn(n_days) * 2) + 10 * np.sin(np.arange(n_days) * 0.2)
        signal = np.clip(signal, 0, 100)
        signals_data[t] = signal
        returns_data[t] = -signal * 0.0015 + np.random.randn(n_days) * 0.02

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print("Rolling IC (20-day window, simulated mean-reversion):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()