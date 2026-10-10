#!/usr/bin/env python3
"""IC Analysis for IV Term Structure Momentum alpha signal.

Tests cross-sectional predictive power of term structure momentum
against forward returns. Requires historical data from main.py runs.
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import json
from datetime import datetime, timedelta

from common.utils import compute_ic, rolling_ic, compute_signal_metrics, half_life_of_mean_reversion

HISTORY_FILE = "data/iv_term_momentum_history.json"


def load_history():
    """Load historical term structure snapshots from JSON file."""
    if not os.path.exists(HISTORY_FILE):
        return {}
    try:
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading history: {e}")
        return {}


def build_signal_panel(history, signal_keys=['momentum_1d', 'momentum_5d', 'momentum_10d', 'slope_zscore']):
    """Build signal DataFrame: rows = dates, columns = tickers, values = signal."""
    all_dates = set()
    for ticker, entries in history.items():
        for e in entries:
            if 'momentum_1d' in e:
                all_dates.add(e['timestamp'][:10])  # YYYY-MM-DD
    
    dates = sorted(all_dates)
    if not dates:
        return {}, {}
    
    signals = {k: pd.DataFrame(index=dates, columns=list(history.keys())) for k in signal_keys}
    
    for ticker, entries in history.items():
        for e in entries:
            if 'momentum_1d' not in e:
                continue
            date = e['timestamp'][:10]
            for k in signal_keys:
                val = e.get(k)
                if val is not None and not pd.isna(val):
                    signals[k].loc[date, ticker] = val
    
    # Convert to numeric
    for k in signal_keys:
        signals[k] = signals[k].apply(pd.to_numeric, errors='coerce')
    
    return signals, dates


def build_forward_returns(dates, tickers, horizon=1):
    """Build forward returns DataFrame for IC computation.
    
    In production, this would fetch actual price data. For now,
    returns a template structure.
    """
    # This would be implemented with actual price data
    # For now, return empty structure
    returns = pd.DataFrame(index=dates, columns=tickers)
    return returns.apply(pd.to_numeric, errors='coerce')


def run_ic_analysis():
    """Run IC analysis on available historical data."""
    print(f"\n📊 IC Analysis — IV Term Structure Momentum")
    print("=" * 60)

    history = load_history()
    if not history:
        print("No historical data found. Run main.py daily to accumulate history.")
        return

    signals, dates = build_signal_panel(history)
    if not dates:
        print("No signal data with momentum computed yet. Need more daily runs.")
        return

    print(f"\nData range: {dates[0]} to {dates[-1]}")
    print(f"Dates: {len(dates)}, Tickers: {list(history.keys())}")

    for signal_name, signal_df in signals.items():
        clean_df = signal_df.dropna(how='all')
        if len(clean_df) < 5:
            print(f"\n{signal_name}: Insufficient data ({len(clean_df)} valid dates)")
            continue

        print(f"\n{signal_name}: {len(clean_df)} valid dates")
        print(f"  Cross-sectional obs per date: {clean_df.count(axis=1).mean():.1f} avg")

        # Need forward returns to compute real IC
        print(f"  ⚠️  Forward returns not yet integrated — cannot compute real IC")
        print(f"  📋 To enable: fetch daily close prices, compute 1d forward returns")

    # Summary
    total_entries = sum(len(v) for v in history.values())
    with_momentum = sum(1 for v in history.values() for e in v if 'momentum_1d' in e)
    print(f"\n📈 History: {total_entries} total snapshots, {with_momentum} with momentum")
    print(f"💡 Run main.py daily for {max(0, 20 - len(dates))} more days to enable robust IC")


def compute_ic_from_prices(signals_df, prices_df, horizon=1):
    """Compute IC given signals and price data.
    
    Args:
        signals_df: DataFrame with dates as index, tickers as columns
        prices_df: DataFrame with dates as index, tickers as columns (close prices)
        horizon: Forward return horizon in days
    """
    # Compute forward returns
    forward_returns = prices_df.pct_change(horizon).shift(-horizon)
    
    # Align and stack
    common_dates = signals_df.index.intersection(forward_returns.index)
    common_tickers = signals_df.columns.intersection(forward_returns.columns)
    
    if len(common_dates) < 5 or len(common_tickers) < 3:
        return np.nan
    
    sig_aligned = signals_df.loc[common_dates, common_tickers]
    ret_aligned = forward_returns.loc[common_dates, common_tickers]
    
    # Stack to long format
    sig_stacked = sig_aligned.stack()
    ret_stacked = ret_aligned.stack()
    
    common_idx = sig_stacked.index.intersection(ret_stacked.index)
    if len(common_idx) < 10:
        return np.nan
    
    return sig_stacked.loc[common_idx].rank().corr(ret_stacked.loc[common_idx].rank())


if __name__ == "__main__":
    run_ic_analysis()