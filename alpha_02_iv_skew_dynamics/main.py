#!/usr/bin/env python3
"""IV Skew Dynamics alpha signal.

Tracks put-call IV skew (25-delta put IV - 25-delta call IV) across expirations.
Signal = change in skew vs. forward returns.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from math import erf

from common.universe import TICKERS


RISK_FREE = 0.04          # flat annual rate for delta calc
NEAR_DTE, FAR_DTE = 30, 75  # target tenors (days)
MIN_DTE = 7


def bs_delta(spot, strike, dte, iv, option_type='call', r=RISK_FREE):
    """Black-Scholes delta (no dividends). Puts return negative delta."""
    t = max(dte, 1) / 365.0
    d1 = (np.log(spot / strike) + (r + 0.5 * iv ** 2) * t) / (iv * np.sqrt(t))
    n_d1 = 0.5 * (1 + erf(d1 / np.sqrt(2)))
    return n_d1 if option_type == 'call' else n_d1 - 1


def get_atm_iv_for_delta(chain_df, current_price, dte, target_delta=0.25, option_type='put'):
    """IV at a target |delta|, linearly interpolated between OTM strikes.

    Delta is computed per strike with Black-Scholes using that strike's own IV.
    Only OTM options are used (puts K < S, calls K > S) since ITM IVs are noisy.
    """
    if option_type == 'put':
        candidates = chain_df[chain_df['strike'] < current_price].copy()
    else:
        candidates = chain_df[chain_df['strike'] > current_price].copy()

    if len(candidates) < 2:
        return np.nan

    candidates['abs_delta'] = [
        abs(bs_delta(current_price, k, dte, v, option_type))
        for k, v in zip(candidates['strike'], candidates['impliedVolatility'])
    ]
    candidates = candidates.sort_values('abs_delta')
    d = candidates['abs_delta'].values
    if not (d.min() <= target_delta <= d.max()):
        return np.nan
    return float(np.interp(target_delta, d, candidates['impliedVolatility'].values))


def compute_skew_metrics(ticker_str):
    """Compute IV skew metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Pick the expirations closest to the near/far target tenors (skip < MIN_DTE)
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

        if not valid_exps:
            return None

        targets = []
        for target in (NEAR_DTE, FAR_DTE):
            best = min(valid_exps, key=lambda x: abs(x[1] - target))
            if best not in targets:
                targets.append(best)
        valid_exps = sorted(targets, key=lambda x: x[0])

        results = []
        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                calls = chain.calls
                puts = chain.puts
                
                # Filter: some liquidity, a live quote, and a sane IV
                def _liquid(df):
                    return df[
                        ((df['volume'].fillna(0) > 0) | (df['openInterest'].fillna(0) > 50)) &
                        (df['bid'].fillna(0) > 0) &
                        (df['impliedVolatility'] > 0.03) & (df['impliedVolatility'] < 3.0)
                    ].copy()
                calls = _liquid(calls)
                puts = _liquid(puts)
                
                if len(calls) < 5 or len(puts) < 5:
                    continue
                
                # Get 25-delta put and call IV
                put_25d = get_atm_iv_for_delta(puts, current_price, dte, 0.25, 'put')
                call_25d = get_atm_iv_for_delta(calls, current_price, dte, 0.25, 'call')
                
                if pd.isna(put_25d) or pd.isna(call_25d):
                    continue
                
                # Skew = put IV - call IV (positive = put premium / fear)
                skew = put_25d - call_25d
                
                # Also compute ATM IV for reference
                # ignore_index: calls/puts share index labels, so .loc would return a Series
                both = pd.concat([calls, puts], ignore_index=True)
                atm_iv = both.loc[(both['strike'] - current_price).abs().idxmin(), 'impliedVolatility']
                
                results.append({
                    'expiration': exp_str,
                    'dte': dte,
                    'put_25d_iv': put_25d,
                    'call_25d_iv': call_25d,
                    'skew_25d': skew,
                    'atm_iv': atm_iv if pd.notna(atm_iv) else np.nan,
                })
            except Exception as e:
                print(f"  ⚠️ {ticker_str} {exp_str}: {type(e).__name__}: {e}")
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