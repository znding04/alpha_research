#!/usr/bin/env python3
"""IC Analysis for IV Dispersion signal.

Computes Information Coefficient between IV dispersion and forward returns.
Requires historical dispersion data (run main.py daily to build history).
"""

import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json

from common.utils import compute_ic, compute_signal_metrics


HISTORY_PATH = "data/iv_dispersion_history.json"
TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def load_dispersion_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_dispersion_history(history):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, 'w') as f:
        json.dump(history, f, indent=2)


def compute_forward_returns(ticker, start_date, horizon_days=5):
    """Compute forward returns from start_date."""
    try:
        tq = yf.Ticker(ticker)
        hist = tq.history(period="60d")
        if len(hist) < horizon_days + 5:
            return np.nan
        close = hist['Close']
        start_price = close.loc[start_date] if start_date in close.index else close.iloc[0]
        end_price = close.iloc[-1]
        return np.log(end_price / start_price) if start_price > 0 else np.nan
    except Exception:
        return np.nan


def update_history_with_returns(history):
    """Add forward returns to historical dispersion entries."""
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")

    for index in ['SPY', 'QQQ']:
        if index not in history:
            continue

        updated_entries = []
        for entry in history[index]:
            if entry['date'] < cutoff:
                continue

            # Compute 5-day forward return if not already present
            if 'fwd_ret_5d' not in entry:
                entry['fwd_ret_5d'] = compute_forward_returns(index, entry['date'], 5)

            updated_entries.append(entry)

        history[index] = updated_entries

    return history


def compute_ic_from_history(history, index='SPY', horizon='fwd_ret_5d'):
    """Compute IC from historical dispersion data."""
    if index not in history or len(history[index]) < 20:
        return np.nan, 0

    entries = history[index]
    dispersions = [e['dispersion'] for e in entries if 'dispersion' in e]
    returns = [e[horizon] for e in entries if horizon in e and not np.isnan(e[horizon])]

    if len(dispersions) < 20 or len(returns) < 20:
        return np.nan, len(dispersions)

    # Align by index (assuming same order)
    min_len = min(len(dispersions), len(returns))
    sig = pd.Series(dispersions[:min_len])
    ret = pd.Series(returns[:min_len])

    ic = compute_ic(sig, ret)
    return ic, min_len


if __name__ == "__main__":
    print(f"\n📈 IV Dispersion IC Analysis — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    history = load_dispersion_history()
    history = update_history_with_returns(history)
    save_dispersion_history(history)

    for index in ['SPY', 'QQQ']:
        ic, n = compute_ic_from_history(history, index, 'fwd_ret_5d')
        print(f"\n{index}:")
        if not np.isnan(ic):
            print(f"  IC (5-day forward): {ic:.4f}")
            print(f"  Observations:       {n}")
            metrics = compute_signal_metrics(pd.Series([ic]))
            if 'error' not in metrics:
                print(f"  IR (proxy):         {metrics.get('ir', np.nan):.4f}")
                print(f"  Win Rate:           {metrics.get('win_rate', np.nan):.4f}")
        else:
            print(f"  Insufficient data ({n} observations) — need 20+")

    print(f"\n💡 Note: Run main.py daily to build dispersion history for IC analysis.")
    print(f"   History stored in {HISTORY_PATH}\n")