"""
IC Analysis for IV Term Structure Slope signal.

Computes the Information Coefficient (IC) between the IV term structure slope
and the forward return of the underlying asset. A positive IC indicates that
higher term structure slope is associated with higher forward returns (bullish).
"""
import os
import sys
import numpy as np
import pandas as pd
from datetime import datetime

from common.universe import TICKERS


def compute_ic(slope_series, forward_returns):
    """
    Compute Information Coefficient between IV term structure slope and forward returns.
    
    IC = correlation(slope, forward_returns)
    """
    if len(slope_series) < 2 or len(forward_returns) < 2:
        return None
    
    # Align by index (ticker order)
    slope_series = slope_series.sort_index()
    forward_returns = forward_returns.sort_index()
    
    # Align on common tickers
    common = slope_series.index.intersection(forward_returns.index)
    if len(common) < 2:
        return None
    
    slope_aligned = slope_series.loc[common]
    forward_aligned = forward_returns.loc[common]
    
    # Compute correlation
    ic = np.corrcoef(slope_aligned, forward_aligned)[0, 1]
    
    return {
        'ic': float(ic),
        'slope': float(slope_aligned.iloc[-1]),
        'forward_returns': forward_aligned.tolist(),
        'n_observations': len(common),
    }


def main():
    """Run IC analysis for IV Term Structure Slope signal."""
    print(f"🔍 IC Analysis for IV Term Structure Slope — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Get IV term structure slope data
    slope_results = []
    for ticker in TICKERS:
        result = compute_iv_term_structure_slope(ticker)
        if result:
            slope_results.append(result)
    
    if not slope_results:
        print("❌ No slope data available")
        return
    
    # Sort by slope (most positive first)
    slope_results.sort(key=lambda x: x['term_structure_slope'], reverse=True)
    
    print(f"\n📊 IC Analysis — {len(slope_results)} tickers analyzed")
    print("\nTicker | IC | Term Structure Slope | N Observations")
    print("-" * 70)
    
    for r in slope_results:
        print(f"{r['ticker']:12} | {r['ic']:>10.4f} | {r['term_structure_slope']:>14} | {r['n_expirations']:>12}")
    
    # Save IC analysis results
    df = pd.DataFrame(slope_results)
    df.to_csv('data/iv_term_structure_slope_ic_latest.csv', index=False)
    print("\n✅ Saved IC analysis to data/iv_term_structure_slope_ic_latest.csv")
    print(f"   Total tickers: {len(slope_results)}")


if __name__ == "__main__":
    main()
