#!/usr/bin/env python3
"""IC Analysis for IV Skew Momentum signal.

Computes Information Coefficient between skew momentum and forward returns.
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

from common.utils import compute_ic, rolling_ic, compute_signal_metrics, half_life_of_mean_reversion

HISTORY_FILE = "data/iv_skew_momentum_history.json"
SIGNAL_FILE = "data/iv_skew_momentum_signal_latest.csv"


def load_signal_history():
    """Load signal history from daily snapshots (would need to be built up over time).
    
    For now, this is a template. In production, you'd accumulate daily signal CSVs
    or maintain a proper signal panel DataFrame.
    """
    # This would be built by the cron job over time
    # For now, return empty - need to accumulate data first
    return None


def fetch_forward_returns(tickers, start_date, end_date):
    """Fetch forward returns for tickers over a date range.
    
    Returns DataFrame with dates as columns, tickers as rows (matching signal format).
    """
    returns_data = {}
    for t in tickers:
        try:
            tq = yf.Ticker(t)
            hist = tq.history(start=start_date, end=end_date, interval="1d")
            if len(hist) > 0:
                # Compute forward returns (next day close / today close - 1)
                hist['fwd_ret'] = hist['Close'].pct_change().shift(-1)
                returns_data[t] = hist['fwd_ret']
        except Exception:
            continue
    
    if not returns_data:
        return None
    
    df = pd.DataFrame(returns_data)
    df.index = pd.to_datetime(df.index).strftime("%Y-%m-%d")
    return df.T  # Transpose: tickers as rows, dates as columns


def run_ic_analysis():
    """Run IC analysis on accumulated signal history."""
    print(f"\n📊 IV Skew Momentum IC Analysis — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load signal history (placeholder - needs accumulated data)
    signal_history = load_signal_history()
    
    if signal_history is None:
        print("\n⚠️  No signal history available yet.")
        print("   Run main.py daily to accumulate history.")
        print("   Need at least 20-30 days of data for meaningful IC.")
        return
    
    # For demonstration, show how analysis would work
    print("\n📋 IC Analysis Framework Ready")
    print("   Once history accumulates, this will compute:")
    print("   - Cross-sectional IC (Spearman rank correlation)")
    print("   - Rolling IC time series")
    print("   - Information Ratio (IC mean / IC std)")
    print("   - Half-life of signal decay")
    print("   - Win rate, max/min IC")


if __name__ == "__main__":
    run_ic_analysis()