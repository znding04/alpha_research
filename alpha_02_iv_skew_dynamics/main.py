#!/usr/bin/env python3
"""IV Skew Dynamics alpha signal.

Tracks put-call IV skew (25-delta put IV - 25-delta call IV) across expirations.
Signal = change in skew vs. forward returns.
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_atm_iv_for_delta(chain_df, current_price, target_delta=0.25, option_type='put'):
    """Approximate delta by finding strike closest to target delta moneyness.
    
    For puts: 25-delta ≈ strike ~ 0.95 * spot (OTM)
    For calls: 25-delta ≈ strike ~ 1.05 * spot (OTM)
    """
    if option_type == 'put':
        target_strike = current_price * 0.95
        candidates = chain_df[chain_df['strike'] < current_price]
    else:
        target_strike = current_price * 1.05
        candidates = chain_df[chain_df['strike'] > current_price]
    
    if len(candidates) == 0:
        return np.nan
    
    idx = (candidates['strike'] - target_strike).abs().idxmin()
    row = candidates.loc[idx]
    return row['impliedVolatility'] if pd.notna(row['impliedVolatility']) else np.nan


def compute_skew_metrics(ticker_str):
    """Compute IV skew metrics for a single ticker."""
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
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append((d, (d - now).days))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
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
                    (calls['volume'] > 10) | (calls['openInterest'] > 100)
                ].copy()
                puts = puts[
                    (puts['volume'] > 10) | (puts['openInterest'] > 100)
                ].copy()
                
                if len(calls) < 5 or len(puts) < 5:
                    continue
                
                # Get 25-delta put and call IV
                put_25d = get_atm_iv_for_delta(puts, current_price, 0.25, 'put')
                call_25d = get_atm_iv_for_delta(calls, current_price, 0.25, 'call')
                
                if pd.isna(put_25d) or pd.isna(call_25d):
                    continue
                
                # Skew = put IV - call IV (positive = put premium / fear)
                skew = put_25d - call_25d
                
                # Also compute ATM IV for reference
                atm_strike_idx = (pd.concat([calls, puts])['strike'] - current_price).abs().idxmin()
                atm_iv = pd.concat([calls, puts]).loc[atm_strike_idx, 'impliedVolatility']
                
                results.append({
                    'expiration': exp_str,
                    'dte': dte,
                    'put_25d_iv': put_25d,
                    'call_25d_iv': call_25d,
                    'skew_25d': skew,
                    'atm_iv': atm_iv if pd.notna(atm_iv) else np.nan,
                })
            except Exception:
                continue
        
        if not results:
            return None
        
        df = pd.DataFrame(results)
        df = df.sort_values('dte')
        
        # Key metrics
        near_skew = df.iloc[0]['skew_25d'] if len(df) > 0 else np.nan
        far_skew = df.iloc[-1]['skew_25d'] if len(df) > 1 else np.nan
        term_structure_slope = (far_skew - near_skew) / (df.iloc[-1]['dte'] - df.iloc[0]['dte']) if len(df) > 1 else np.nan
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'near_skew_25d': round(near_skew, 4),
            'far_skew_25d': round(far_skew, 4),
            'skew_term_slope': round(term_structure_slope, 6),
            'n_expirations': len(df),
            'skew_by_dte': df.to_dict('records'),
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 IV Skew Dynamics Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_skew_metrics(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  Near-term skew (25d): {r['near_skew_25d']:.4f}")
        print(f"  Far-term skew (25d):  {r['far_skew_25d']:.4f}")
        print(f"  Skew term slope:      {r['skew_term_slope']:.6f}")
        print(f"  Expirations:          {r['n_expirations']}")
    
    # Save detailed data
    os.makedirs("data", exist_ok=True)
    path = "data/iv_skew_latest.csv"
    
    # Flatten for CSV
    flat_rows = []
    for r in results:
        for exp_data in r['skew_by_dte']:
            flat_rows.append({
                'ticker': r['ticker'],
                'current_price': r['current_price'],
                'expiration': exp_data['expiration'],
                'dte': exp_data['dte'],
                'put_25d_iv': exp_data['put_25d_iv'],
                'call_25d_iv': exp_data['call_25d_iv'],
                'skew_25d': exp_data['skew_25d'],
                'atm_iv': exp_data['atm_iv'],
            })
    
    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved detailed data to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")