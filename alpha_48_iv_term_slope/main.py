#!/usr/bin/env python3
"""Compute IV Term Structure Slope alpha signal.

Signal = ATM IV spread between short-dated and longer-dated expiries.
Positive slope (short > long) = steep term structure → mean-reversion short vol.
Negative slope (long > short) = inverted → mean-reversion long vol.
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


def compute_atm_iv_for_expiration(ticker_str, target_exp):
    """Compute ATM IV for a specific expiration date string."""
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        chain = tq.option_chain(target_exp)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        
        # Fix dtypes: volume/OI are numpy int64
        df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        
        # Filter: liquid + valid IV + positive price + reasonable IV
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()
        
        if len(df) < 10:
            return None
        
        # Robust ATM IV: median of strikes within ±2% moneyness with IV > 5%
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
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'atm_iv': round(atm_iv, 4),
            'n_contracts': len(df),
            'expiration': target_exp,
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str} {target_exp}: {e}")
        return None


def get_valid_expirations(ticker_str):
    """Get valid expiration dates for a ticker within 2-180 days."""
    try:
        tq = yf.Ticker(ticker_str)
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                if d.date() > now.date() and (d - now).days <= 180 and (d - now).days > 2:
                    valid_exps.append(d)
            except ValueError:
                continue
        valid_exps.sort()
        return valid_exps
    except Exception:
        return []


def find_short_long_expirations(valid_exps):
    """Find short-dated (7-30 DTE) and long-dated (30-90 DTE) expirations."""
    now = datetime.now()
    
    short_candidates = [e for e in valid_exps if 7 <= (e - now).days <= 30]
    long_candidates = [e for e in valid_exps if 30 <= (e - now).days <= 90]
    
    short_exp = min(short_candidates, default=None)
    long_exp = min(long_candidates, default=None)
    
    return short_exp, long_exp


if __name__ == "__main__":
    print(f"\n🔍 IV Term Structure Slope — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        valid_exps = get_valid_expirations(t)
        
        if not valid_exps:
            print(f"  {t}: No valid expirations")
            continue
        
        short_exp, long_exp = find_short_long_expirations(valid_exps)
        
        if short_exp is None or long_exp is None:
            print(f"  {t}: Could not find both short ({short_exp}) and long ({long_exp}) exp")
            continue
        
        short_str = short_exp.strftime("%Y-%m-%d")
        long_str = long_exp.strftime("%Y-%m-%d")
        
        short_data = compute_atm_iv_for_expiration(t, short_str)
        long_data = compute_atm_iv_for_expiration(t, long_str)
        
        if short_data is None or long_data is None:
            print(f"  {t}: Failed to compute ATM IV for one or both expiries")
            continue
        
        short_iv = short_data['atm_iv']
        long_iv = long_data['atm_iv']
        
        # Slope: short IV - long IV (positive = steep/contango, negative = inverted/backwardation)
        slope = short_iv - long_iv
        slope_pct = slope / long_iv if long_iv > 0 else 0
        
        dte_short = (short_exp - datetime.now()).days
        dte_long = (long_exp - datetime.now()).days
        
        result = {
            'ticker': t,
            'current_price': short_data['current_price'],
            'short_iv': short_iv,
            'long_iv': long_iv,
            'slope': round(slope, 4),
            'slope_pct': round(slope_pct, 4),
            'dte_short': dte_short,
            'dte_long': dte_long,
            'n_contracts_short': short_data['n_contracts'],
            'n_contracts_long': long_data['n_contracts'],
        }
        results.append(result)
        
        print(f"  {t}: Short({dte_short}d)={short_iv:.4f} Long({dte_long}d)={long_iv:.4f} Slope={slope:+.4f} ({slope_pct:+.2%})")
    
    if not results:
        print("No data collected.")
        exit(1)
    
    df = pd.DataFrame(results)
    print(f"\n{'Ticker':<6} {'Price':>8} {'Short IV':>8} {'Long IV':>8} {'Slope':>8} {'Slope%':>8} {'Short DTE':>9} {'Long DTE':>8}")
    print("-" * 80)
    for _, r in df.iterrows():
        print(f"{r['ticker']:<6} {r['current_price']:>8.2f} {r['short_iv']:>8.4f} {r['long_iv']:>8.4f} {r['slope']:>+8.4f} {r['slope_pct']:>+8.2%} {r['dte_short']:>9d} {r['dte_long']:>8d}")
    
    print("\n💡 Interpretation:")
    print("   slope > 0 (steep/contango) → short-term IV > long-term → mean-reversion SHORT vol")
    print("   slope < 0 (inverted/backwardation) → long-term IV > short-term → mean-reversion LONG vol")
    print("   |slope| > 0.05 (5 pts) → strong signal")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_term_slope_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.15-0.40 per run\n")