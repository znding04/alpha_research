#!/usr/bin/env python3
"""IC Analysis for VRP Term Structure alpha signal.

Computes Information Coefficients between VRP term structure metrics
and forward equity returns across the ticker universe.
"""

import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")
import sys
sys.path.insert(0, "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from common.utils import compute_ic, rolling_ic, compute_signal_metrics

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]

# Signal fields to test
SIGNAL_FIELDS = [
    'vrp_slope',        # VRP term structure slope
    'vrp_curvature',    # VRP term structure curvature
    'vrp_spread',       # Far - near VRP spread
    'avg_vrp_var',      # Average VRP variance across term
    'avg_vrp_vol',      # Average VRP vol points across term
    'avg_vrp_ratio',    # Average VRP ratio (IV^2/RV^2)
    'near_vrp_var',     # Near-term VRP variance
    'far_vrp_var',      # Far-term VRP variance
]


def load_historical_signals(data_dir="data"):
    """Load historical signal data from CSV files."""
    import glob
    files = glob.glob(os.path.join(data_dir, "vrp_term_structure_*.csv"))
    if not files:
        return None
    
    # For now, we only have latest - this would need historical runs
    # In production, you'd accumulate daily snapshots
    return None


def compute_forward_returns(tickers, forward_days=5):
    """Compute forward returns for each ticker."""
    returns = {}
    end_date = datetime.now()
    start_date = end_date - timedelta(days=forward_days + 10)  # extra for weekends
    
    for t in tickers:
        try:
            tq = yf.Ticker(t)
            hist = tq.history(start=start_date.strftime("%Y-%m-%d"), 
                              end=end_date.strftime("%Y-%m-%d"))
            if len(hist) >= 2:
                close = hist['Close']
                # Forward return: (price_t+forward / price_t) - 1
                # For latest data, we use the most recent return as proxy
                ret = (close.iloc[-1] / close.iloc[-2]) - 1
                returns[t] = ret
        except Exception:
            returns[t] = np.nan
    return pd.Series(returns, name=f'forward_{forward_days}d')


def run_cross_sectional_ic(signals_df, forward_days=5):
    """Run cross-sectional IC analysis for a single date."""
    signals_date = signals_df.iloc[:, 0]  # Assuming single date column
    
    # Get forward returns
    forward_rets = compute_forward_returns(TICKERS, forward_days)
    
    results = {}
    for field in SIGNAL_FIELDS:
        if field in signals_date.index:
            signal_vals = signals_date[field]
            if pd.notna(signal_vals).sum() >= 3:
                ic = compute_ic(signal_vals.dropna(), forward_rets.dropna())
                results[field] = ic
    return results


def generate_sample_ic_analysis():
    """Generate a template IC analysis using current data."""
    print("\n📈 VRP Term Structure IC Analysis")
    print("=" * 60)
    print("Note: This requires historical signal data accumulated over time.")
    print("Run main.py daily to build history, then analyze.\n")
    
    print("Signal fields to test:")
    for f in SIGNAL_FIELDS:
        print(f"  - {f}")
    
    print("\nExpected relationships:")
    print("  vrp_slope < 0 (inverted) → Positive forward returns (mean reversion)")
    print("  vrp_slope > 0 (normal)   → Negative forward returns (complacency)")
    print("  vrp_spread (far-near)    → Negative IC (inverted predicts outperformance)")
    print("  avg_vrp_var (high)       → Positive forward returns (fear premium)")
    print("  avg_vrp_ratio (high)     → Positive forward returns (expensive vol)")
    
    print("\nTo build IC history:")
    print("  1. Run main.py daily (cron job)")
    print("  2. Archive daily snapshots to data/vrp_term_structure_YYYYMMDD.csv")
    print("  3. Run this analysis monthly with accumulated data")
    
    return None


if __name__ == "__main__":
    generate_sample_ic_analysis()