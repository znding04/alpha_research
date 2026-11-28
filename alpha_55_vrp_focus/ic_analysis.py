#!/usr/bin/env python3
"""IC analysis for VRP alpha signal (alpha_55_vrp_focus).

Compares cross-sectional VRP rank with 5-day forward returns.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

from common.utils import ic, rolling_ic
from common.universe import FOCUS_TICKERS


def load_latest_vrp():
    """Load latest VRP snapshot from data/vrp55_latest.csv."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "vrp55_latest.csv")
    if not os.path.exists(path):
        return None
    return pd.read_csv(path)


def compute_forward_returns(tickers, days=5):
    """5-day forward returns for each ticker."""
    rets = {}
    for t in tickers:
        hist = yf.Ticker(t).history(period="3mo", interval="1d")
        if hist.empty or len(hist) < days + 1:
            continue
        closes = hist['Close'].dropna()
        if len(closes) < days + 1:
            continue
        ret = (closes.iloc[-1] / closes.iloc[-days-1]) - 1
        rets[t] = ret
    return rets


def main():
    df = load_latest_vrp()
    if df is None:
        print("No VRP snapshot found at data/vrp55_latest.csv")
        return

    # Add forward returns
    fwd = compute_forward_returns(FOCUS_TICKERS, days=5)
    df['fwd_ret_5d'] = df['ticker'].map(fwd)

    # Drop rows with missing fwd returns
    df = df.dropna(subset=['fwd_ret_5d'])

    # IC between VRP rank (as negative of VRP to test mean reversion) and fwd returns
    # Negative VRP => cheap options => possible outperformance => positive fwd return
    # So we expect negative IC between VRP and fwd returns
    vrp_ic = ic(df['vrp_variance'], df['fwd_ret_5d'])
    ratio_ic = ic(df['vrp_ratio'], df['fwd_ret_5d'])

    print("\n📈 VRP IC Analysis (5-day forward returns)")
    print("=" * 50)
    print(f"   VRP (variance) IC: {vrp_ic:+.4f}")
    print(f"   VRP ratio IC:     {ratio_ic:+.4f}")
    print("\n   Interpretation: negative IC suggests high VRP predicts lower forward returns (mean reversion).")


if __name__ == "__main__":
    main()