#!/usr/bin/env python3
"""Compute IV Rank alpha signal for a watchlist of tickers."""
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


def compute_iv_rank(ticker_str):
    """Compute IV rank metric for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Fetch option chains - take most liquid expiration
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append(d)
            except ValueError:
                continue
        valid_exps.sort()
        
        if not valid_exps:
            return None
        
        # Use nearest meaningful expiration (skip DTE < 2)
        target_exp = min(
            [e for e in valid_exps if e > datetime.now().replace(day=max(now.day, 2))],
            default=valid_exps[0]
        )
        target_str = target_exp.strftime("%Y-%m-%d")
        
        chain = tq.option_chain(target_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        
        # Fix dtypes: both volume and openInterest are float64 with NaN (not int64)
        # Comparison works directly on float64 after fillna; avoid .astype(int) which fails on NaN/inf
        df['volume'] = df['volume'].fillna(0)
        df['openInterest'] = df['openInterest'].fillna(0)
        
        # Filter: liquid + valid IV + positive price + reasonable IV (not near-zero)
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &  # repo-standard liquidity; >50/>500 dropped thin ETF chains (FXI, GDX)
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &  # Filter out near-zero IV (bid=ask=0)
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()
        
        if len(df) < 10:
            return None
        
        # Robust ATM IV: median of strikes within ±2% moneyness with reasonable IV (>5%)
        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
        
        if len(atm_candidates) >= 3:
            atm_iv = atm_candidates['impliedVolatility'].median()
        else:
            # Fallback: single closest strike with IV > 0.05
            valid_strikes = df[df['impliedVolatility'] > 0.05]
            if len(valid_strikes) == 0:
                return None
            atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
            atm_iv = valid_strikes.loc[atm_idx, 'impliedVolatility']
        
        median_iv = df['impliedVolatility'].median()
        iv_spread = atm_iv - median_iv
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'atm_iv': round(atm_iv, 4),
            'median_iv': round(median_iv, 4),
            'iv_spread': round(iv_spread, 4),
            'n_contracts': len(df),
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n🔍 IV Rank Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_iv_rank(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   iv_spread > 0 → ATM vol premium (convexity risk)")
    print("   iv_spread < 0 → OTM vol premium (tail-hedge demand)")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_rank_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")
