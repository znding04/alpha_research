#!/usr/bin/env python3
"""IV Term Structure Slope alpha signal.

Tracks ATM IV curve slope (short vs long DTE) as mean-reversion signal.
Signal = (IV_long - IV_short) / (DTE_long - DTE_short) — positive = normal contango,
negative = backwardation (fear/stress).
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
MIN_DTE = 7  # skip expiring/weekly-noise legs (0-DTE IV is unreliable)
# Regime thresholds on term_ratio = far_IV / near_IV (unit-free)
CONTANGO_RATIO = 1.03       # far IV ≥ 3% above near → contango
BACKWARDATION_RATIO = 0.97  # far IV ≥ 3% below near → backwardation


def compute_atm_iv(chain_df, current_price):
    """Compute ATM IV for a given option chain."""
    if len(chain_df) == 0:
        return np.nan
    # Find strike closest to current price
    idx = (chain_df['strike'] - current_price).abs().idxmin()
    row = chain_df.loc[idx]
    iv = row['impliedVolatility']
    return iv if pd.notna(iv) and iv > 0.01 else np.nan


def compute_term_structure(ticker_str):
    """Compute IV term structure metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Get all valid expirations within 180 days
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d.date() - now.date()).days
                if MIN_DTE <= dte <= 180:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if len(valid_exps) < 2:
            return None
        
        results = []
        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                calls = chain.calls
                puts = chain.puts
                
                # Filter liquid options
                calls = calls[
                    (calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)
                ].copy()
                puts = puts[
                    (puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)
                ].copy()
                
                if len(calls) < 5 or len(puts) < 5:
                    continue
                
                # Compute ATM IV for calls and puts, average them
                call_atm_iv = compute_atm_iv(calls, current_price)
                put_atm_iv = compute_atm_iv(puts, current_price)
                
                if pd.isna(call_atm_iv) and pd.isna(put_atm_iv):
                    continue
                
                # Use available IV (prefer average of both)
                atm_ivs = [iv for iv in [call_atm_iv, put_atm_iv] if not pd.isna(iv)]
                atm_iv = np.mean(atm_ivs)
                
                results.append({
                    'expiration': exp_str,
                    'dte': dte,
                    'atm_iv': atm_iv,
                    'call_atm_iv': call_atm_iv,
                    'put_atm_iv': put_atm_iv,
                })
            except Exception:
                continue
        
        if len(results) < 2:
            return None
        
        df = pd.DataFrame(results)
        df = df.sort_values('dte')
        
        # Key metrics
        near_iv = df.iloc[0]['atm_iv']
        far_iv = df.iloc[-1]['atm_iv']
        near_dte = df.iloc[0]['dte']
        far_dte = df.iloc[-1]['dte']
        
        # Term structure slope: (far_iv - near_iv) / (far_dte - near_dte)
        # Positive = normal contango (IV increases with time)
        # Negative = backwardation (near-term IV > far-term IV = stress/fear)
        # Units: IV (decimal) per calendar day. ×30 → vol change per month.
        term_slope = (far_iv - near_iv) / (far_dte - near_dte) if far_dte != near_dte else np.nan
        term_ratio = far_iv / near_iv if near_iv > 0 else np.nan
        
        # Also compute curvature (3-point if available)
        curvature = np.nan
        if len(df) >= 3:
            mid_idx = len(df) // 2
            mid_iv = df.iloc[mid_idx]['atm_iv']
            mid_dte = df.iloc[mid_idx]['dte']
            # Second derivative approximation
            curvature = (far_iv - 2*mid_iv + near_iv) / ((far_dte - mid_dte) * (mid_dte - near_dte))
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'near_atm_iv': round(near_iv, 4),
            'far_atm_iv': round(far_iv, 4),
            'near_dte': int(near_dte),
            'far_dte': int(far_dte),
            'term_slope': round(term_slope, 6),
            'term_ratio': round(term_ratio, 4),
            'term_curvature': round(curvature, 8) if not pd.isna(curvature) else np.nan,
            'n_expirations': len(df),
            'term_structure': df.to_dict('records'),
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📈 IV Term Structure Slope Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_term_structure(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        slope_str = f"{r['term_slope']:.6f}"
        curve_str = f"{r['term_curvature']:.8f}" if not pd.isna(r['term_curvature']) else "N/A"
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  Near ATM IV ({r['near_dte']}d): {r['near_atm_iv']:.4f}")
        print(f"  Far ATM IV  ({r['far_dte']}d):  {r['far_atm_iv']:.4f}")
        print(f"  Term slope (per day): {slope_str}")
        print(f"  Term curvature:       {curve_str}")
        print(f"  Expirations:          {r['n_expirations']}")
        
        # Interpretation
        print(f"  Term ratio (far/near): {r['term_ratio']:.4f}")
        if r['term_ratio'] < BACKWARDATION_RATIO:
            print(f"  📉 BACKWARDATION — Near-term IV premium (stress/fear)")
        elif r['term_ratio'] > CONTANGO_RATIO:
            print(f"  📈 CONTANGO — Normal term structure (IV rises with time)")
        else:
            print(f"  ➖ FLAT — Minimal term structure")
    
    # Save detailed data
    os.makedirs("data", exist_ok=True)
    path = "data/iv_term_structure_latest.csv"
    
    # Flatten for CSV
    flat_rows = []
    for r in results:
        for exp_data in r['term_structure']:
            flat_rows.append({
                'ticker': r['ticker'],
                'current_price': r['current_price'],
                'expiration': exp_data['expiration'],
                'dte': exp_data['dte'],
                'atm_iv': exp_data['atm_iv'],
                'call_atm_iv': exp_data['call_atm_iv'],
                'put_atm_iv': exp_data['put_atm_iv'],
            })
    
    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved detailed data to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")