#!/usr/bin/env python3
"""Compute IC for IV Rank Percentile (30d) signal."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from common.ic_engine import cross_sectional_ic
from common.utils import align_signal_and_forward_returns

def load_latest_signal(path="data/iv_rank_percentile_30d_latest.csv"):
    if not os.path.exists(path): return None
    df = pd.read_csv(path)
    df['date'] = pd.Timestamp.now().date()
    return df

def compute_ic_historical(tickers="15"): pass

def run_ic_analysis(ticker_universe="15"):
    # Load recent snapshots; placeholder implementation
    print("IV Rank Percentile (30d) IC analysis — placeholder")
    print("Requires >20 live snapshots to compute IC.")
    # TODO: accumulate snapshots from data/ (historical snapshots)
