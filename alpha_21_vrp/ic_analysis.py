#!/usr/bin/env python3
"""IC Analysis for VRP Change (alpha_21_vrp).

Tests whether the day-over-day change in Variance Risk Premium
(VRP = IV^2 - RV^2) predicts forward returns.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import json
import numpy as np
import pandas as pd
from datetime import datetime
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_returns_available, signal_as_of

from common.universe import TICKERS

HISTORY_FILE = "data/vrp_change_history.json"
LOOKBACK_DAYS = 5


def load_history():
    """Load stored VRP history (written by main.py on every run)."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def build_signal_series(history, lookback=LOOKBACK_DAYS):
    """Build the daily VRP-change signal series from stored history.

    Returns a dict {ticker: {date: vrp_change}}.
    """
    daily = {}
    for ticker, entries in history.items():
        for e in entries:
            daily.setdefault(e['date'], {})[ticker] = float(e['vrp'])

    dates = sorted(daily.keys())
    if len(dates) < lookback + 1:
        return {}, dates

    signals = {}
    for i in range(lookback, len(dates)):
        date, past = dates[i], dates[i - lookback]
        for t in TICKERS:
            if t in daily[date] and t in daily[past] and daily[past][t] != 0:
                signals.setdefault(t, {})[date] = daily[date][t] - daily[past][t]
    return signals, dates


def run_ic_analysis():
    """Run IC analysis on the latest VRP-change snapshot vs forward returns."""
    print(f"\n📈 IC Analysis — VRP Change — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    snap_path = "data/vrp_change_latest.csv"
    if not os.path.exists(snap_path):
        print(f"❌ No VRP-change data found at {snap_path}. Run main.py first.")
        return None

    df = pd.read_csv(snap_path)
    as_of = signal_as_of(snap_path)
    signals = df.set_index('ticker')['vrp_change_1d']

    print("\nVRP change (1-day) signals:")
    print(signals.to_string())

    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {t: get_forward_returns(t, 5, as_of) for t in TICKERS}
    for t, v in forward_returns.items():
        print(f"  {t}: {v:.4f}" if pd.notna(v) else f"  {t}: N/A")

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]

    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]

    if len(signals) < 3:
        print("\n⚠️ Insufficient data for IC (need ≥3 tickers with valid signals)")
        return None

    ic = compute_ic(signals, returns)
    print(f"\n📊 Information Coefficient (5-day forward): {ic:.4f}")
    print("\nNote: a single snapshot has too few observations for a meaningful IC.")
    print("      Real IC needs the daily history file to build up (≥30–60 sessions).")

    # Historical series check
    history = load_history()
    sig_series, dates = build_signal_series(history)
    if sig_series:
        n_dates = len(next(iter(sig_series.values())))
        print(f"      History so far: {len(dates)} sessions, {n_dates} signal observations per ticker.")
    return ic


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(42)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data, returns_data = {}, {}
    for t in TICKERS:
        # VRP change: slow-moving, mean-reverting around a small positive drift
        signal = 0.0002 + np.cumsum(np.random.randn(n_days) * 0.0003) + 0.0001 * np.sin(np.arange(n_days) * 0.25)
        signals_data[t] = signal
        # Rising VRP (fear) -> short-term reversal is NOT assumed; mild positive link
        returns_data[t] = signal * 0.15 + np.random.randn(n_days) * 0.012

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)

    print("Rolling IC (20-day window, simulated):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()
