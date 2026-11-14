#!/usr/bin/env python3
"""IV Rank Percentile alpha signal.

Hypothesis: Current ATM IV relative to cross-strike IV distribution today approximates
a 60-day percentile ranking. Higher percentile means IV is expensive relative to
todays cross-section, potentially indicating mean-reversion opportunity. Lower
percentile means IV cheap (potential volatility expansion).

Since yfinance provides only current option chains (no historical IV snapshots),
we use today's cross-strike IV spread as a proxy for recent historical range.
In production, store daily option chain snapshots to compute true historical percentiles.

Signal: iv_percentile = (atm_iv - min_iv_proxy) / (max_iv_proxy - min_iv_proxy)
Normalized to 0-1 range, then transformed to percentile (0-100) via (iv_percentile - min) / (max - min).
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

from common.universe import TICKERS

MIN_DTE = 7  # skip weekly/low-liquid expiries
TARGET_DTE = 30  # use expiry closest to this DTE
MAX_DTE = 180  # max DTE to consider


def compute_atm_iv(ticker_str):
    """Get ATM IV from expiration closest to TARGET_DTE."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        
        # Get valid expirations
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d.date() - now.date()).days
                if MIN_DTE <= dte <= MAX_DTE:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        if not valid_exps:
            return None
        
        # Find expiration nearest to TARGET_DTE
        target_exp = min(valid_exps, key=lambda x: abs(x[1] - TARGET_DTE))
        exp_str = target_exp[0].strftime("%Y-%m-%d")
        
        chain = tq.option_chain(exp_str)
        calls = chain.calls
        puts = chain.puts
        
        # Filter liquid options: volume>0 or OI>50, bid>0, IV within bounds
        calls = calls[
            (calls['volume'].fillna(0) > 0) | (calls['openInterest'].fillna(0) > 50)
        ].copy()
        calls = calls[(calls['bid'].fillna(0) > 0)].copy()
        calls = calls[(calls['impliedVolatility'] > 0.01) & (calls['impliedVolatility'] < 3.0)].copy()
        calls = calls[(calls['lastPrice'] > 0)].copy()
        debug_calls = len(calls)
        
        puts = puts[
            (puts['volume'].fillna(0) > 0) | (puts['openInterest'].fillna(0) > 50)
        ].copy()
        puts = puts[(puts['bid'].fillna(0) > 0)].copy()
        puts = puts[(puts['impliedVolatility'] > 0.01) & (puts['impliedVolatility'] < 3.0)].copy()
        puts = puts[(puts['lastPrice'] > 0)].copy()
        debug_puts = len(puts)
        if debug_calls < 5 or debug_puts < 5:
            print(f"  🔍 {ticker_str}: calls={debug_calls} puts={debug_puts}")
        
        if len(calls) < 5 or len(puts) < 5:
            return None
        
        # Combine calls + puts for IV distribution proxy
        both = pd.concat([calls, puts], ignore_index=True)
        both = both.sort_values('impliedVolatility')
        
        # Compute min, max IV for percentile proxy
        min_iv = both['impliedVolatility'].min()
        max_iv = both['impliedVolatility'].max()
        
        # Find ATM strike (closest to current price) and its IV
        atm_idx = (both['strike'] - current_price).abs().idxmin()
        atm_iv = both.loc[atm_idx, 'impliedVolatility']
        
        # Percent within distribution (0-1), but cap to avoid out-of-range due to outliers
        percentile = (atm_iv - min_iv) / (max_iv - min_iv) if max_iv > min_iv else 0.5
        percentile = max(0.0, min(1.0, percentile))
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'atm_iv': round(atm_iv, 4),
            'iv_percentile': round(percentile * 100, 2),  # to percentage 0-100
            'min_iv_proxy': round(min_iv, 4),
            'max_iv_proxy': round(max_iv, 4),
            'n_contracts': len(both),
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📢 IV Rank Percentile Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print(f"Uses cross-strike IV distribution today as proxy for historical range.")
    print(f"Percentile high → IV expensive relative to today’s distribution (potential mean-reversion).")
    print(f"Percentile low → IV cheap relative to today’s distribution (potential vol expansion).")
    
    results = []
    for t in TICKERS:
        r = compute_atm_iv(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  ATM IV: {r['atm_iv']:.4f}")
        print(f"  IV Percentile: {r['iv_percentile']:.2f}%")
        print(f"  Min IV proxy: {r['min_iv_proxy']:.4f}")
        print(f"  Max IV proxy: {r['max_iv_proxy']:.4f}")
        print(f"  n contracts: {r['n_contracts']}")
    
    # Save detailed data
    os.makedirs("data", exist_ok=True)
    path = "data/iv_rank_percentile_latest.csv"
    
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")