#!/usr/bin/env python3
"""Put/Call OI-Weighted IV Spread alpha signal.

Measures the open-interest-weighted IV difference between puts and calls.
Captures dealer/institutional positioning: heavy put OI = hedging demand,
heavy call OI = speculative longs. More robust than raw IV skew because
it weights by actual positioning (OI) rather than quantized IV levels.

Signal = Σ(OI_put × IV_put) / Σ(OI_put) - Σ(OI_call × IV_call) / Σ(OI_call)
       ≈ OI-weighted average put IV - OI-weighted average call IV

Also computes: Put/Call OI Ratio, Put/Call Volume Ratio as flow signals.
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


def compute_positioning_metrics(ticker_str):
    """Compute put/call positioning metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Get valid expirations: 7-45 DTE (focus on liquid monthly/weekly)
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 7 <= dte <= 45:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            # Fallback: nearest expiration with data
            for e in expirations:
                try:
                    d = datetime.strptime(e, "%Y-%m-%d")
                    dte = (d - now).days
                    if 1 <= dte <= 60:
                        valid_exps.append((d, dte))
                except ValueError:
                    continue
            valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            return None
        
        # Aggregate across top 3 liquid expirations
        all_puts = []
        all_calls = []
        exp_count = 0
        
        for exp_date, dte in valid_exps[:3]:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                calls = chain.calls
                puts = chain.puts
                
                # Filter liquid with valid IV and OI/volume
                calls = calls[
                    (calls['impliedVolatility'].notna()) &
                    (calls['impliedVolatility'] > 0.01) &
                    (calls['impliedVolatility'] < 3.0) &
                    ((calls['volume'] > 0) | (calls['openInterest'] > 0))
                ].copy()
                
                puts = puts[
                    (puts['impliedVolatility'].notna()) &
                    (puts['impliedVolatility'] > 0.01) &
                    (puts['impliedVolatility'] < 3.0) &
                    ((puts['volume'] > 0) | (puts['openInterest'] > 0))
                ].copy()
                
                if len(calls) < 5 or len(puts) < 5:
                    continue
                
                # Add expiration info
                calls['expiration'] = exp_str
                calls['dte'] = dte
                puts['expiration'] = exp_str
                puts['dte'] = dte
                
                all_calls.append(calls)
                all_puts.append(puts)
                exp_count += 1
                
            except Exception:
                continue
        
        if exp_count == 0:
            return None
        
        calls_df = pd.concat(all_calls, ignore_index=True) if all_calls else pd.DataFrame()
        puts_df = pd.concat(all_puts, ignore_index=True) if all_puts else pd.DataFrame()
        
        if len(calls_df) == 0 or len(puts_df) == 0:
            return None
        
        # Fill NaN OI/volume with 0
        for df in [calls_df, puts_df]:
            df['openInterest'] = df['openInterest'].fillna(0)
            df['volume'] = df['volume'].fillna(0)
        
        # OI-weighted average IV
        put_oi_total = puts_df['openInterest'].sum()
        call_oi_total = calls_df['openInterest'].sum()
        put_vol_total = puts_df['volume'].sum()
        call_vol_total = calls_df['volume'].sum()
        
        if put_oi_total > 0:
            oi_weighted_put_iv = (puts_df['openInterest'] * puts_df['impliedVolatility']).sum() / put_oi_total
        else:
            oi_weighted_put_iv = puts_df['impliedVolatility'].mean()
        
        if call_oi_total > 0:
            oi_weighted_call_iv = (calls_df['openInterest'] * calls_df['impliedVolatility']).sum() / call_oi_total
        else:
            oi_weighted_call_iv = calls_df['impliedVolatility'].mean()
        
        # Volume-weighted average IV
        if put_vol_total > 0:
            vol_weighted_put_iv = (puts_df['volume'] * puts_df['impliedVolatility']).sum() / put_vol_total
        else:
            vol_weighted_put_iv = puts_df['impliedVolatility'].mean()
        
        if call_vol_total > 0:
            vol_weighted_call_iv = (calls_df['volume'] * calls_df['impliedVolatility']).sum() / call_vol_total
        else:
            vol_weighted_call_iv = calls_df['impliedVolatility'].mean()
        
        # Simple median IV (unweighted)
        median_put_iv = puts_df['impliedVolatility'].median()
        median_call_iv = calls_df['impliedVolatility'].median()
        
        # Spreads
        oi_iv_spread = oi_weighted_put_iv - oi_weighted_call_iv
        vol_iv_spread = vol_weighted_put_iv - vol_weighted_call_iv
        median_iv_spread = median_put_iv - median_call_iv
        
        # Ratios
        oi_ratio = put_oi_total / call_oi_total if call_oi_total > 0 else np.inf
        vol_ratio = put_vol_total / call_vol_total if call_vol_total > 0 else np.inf
        
        # ATM IV for normalization
        all_df = pd.concat([puts_df, calls_df], ignore_index=True)
        moneyness = all_df['strike'] / current_price
        atm = all_df[(moneyness >= 0.98) & (moneyness <= 1.02) & (all_df['impliedVolatility'] > 0.01)]
        atm_iv = atm['impliedVolatility'].median() if len(atm) > 0 else np.nan
        
        # Normalized spreads
        oi_iv_spread_norm = oi_iv_spread / atm_iv if atm_iv and atm_iv > 0 else np.nan
        vol_iv_spread_norm = vol_iv_spread / atm_iv if atm_iv and atm_iv > 0 else np.nan
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'expirations_used': exp_count,
            'atm_iv': round(atm_iv, 4) if pd.notna(atm_iv) else np.nan,
            'put_oi_total': int(put_oi_total),
            'call_oi_total': int(call_oi_total),
            'put_vol_total': int(put_vol_total),
            'call_vol_total': int(call_vol_total),
            'oi_ratio': round(oi_ratio, 4) if np.isfinite(oi_ratio) else np.nan,
            'vol_ratio': round(vol_ratio, 4) if np.isfinite(vol_ratio) else np.nan,
            'oi_weighted_put_iv': round(oi_weighted_put_iv, 4),
            'oi_weighted_call_iv': round(oi_weighted_call_iv, 4),
            'vol_weighted_put_iv': round(vol_weighted_put_iv, 4),
            'vol_weighted_call_iv': round(vol_weighted_call_iv, 4),
            'median_put_iv': round(median_put_iv, 4),
            'median_call_iv': round(median_call_iv, 4),
            'oi_iv_spread': round(oi_iv_spread, 6),
            'vol_iv_spread': round(vol_iv_spread, 6),
            'median_iv_spread': round(median_iv_spread, 6),
            'oi_iv_spread_norm': round(oi_iv_spread_norm, 6) if pd.notna(oi_iv_spread_norm) else np.nan,
            'vol_iv_spread_norm': round(vol_iv_spread_norm, 6) if pd.notna(vol_iv_spread_norm) else np.nan,
            'n_put_contracts': len(puts_df),
            'n_call_contracts': len(calls_df),
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 Put/Call OI-Weighted IV Spread — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_positioning_metrics(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}, {r['expirations_used']} exps):")
        print(f"  ATM IV:              {r['atm_iv']:.4f}")
        print(f"  Put/Call OI Ratio:   {r['oi_ratio']:.4f} (Put OI: {r['put_oi_total']:,} / Call OI: {r['call_oi_total']:,})")
        print(f"  Put/Call Vol Ratio:  {r['vol_ratio']:.4f} (Put Vol: {r['put_vol_total']:,} / Call Vol: {r['call_vol_total']:,})")
        print(f"  OI-wt Put IV:        {r['oi_weighted_put_iv']:.4f}")
        print(f"  OI-wt Call IV:       {r['oi_weighted_call_iv']:.4f}")
        print(f"  OI IV Spread:        {r['oi_iv_spread']:.6f} (norm: {r['oi_iv_spread_norm']:.6f})")
        print(f"  Vol IV Spread:       {r['vol_iv_spread']:.6f} (norm: {r['vol_iv_spread_norm']:.6f})")
        print(f"  Median IV Spread:    {r['median_iv_spread']:.6f}")
        print(f"  Contracts:           {r['n_put_contracts']}P / {r['n_call_contracts']}C")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/oi_weighted_iv_spread_latest.csv"
    
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")