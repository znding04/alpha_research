#!/usr/bin/env python3
"""IV Skew Convexity (Butterfly Skew) alpha signal.

Measures the convexity/curvature of the put-call IV skew across moneyness.
While standard skew = 25d_put_IV - 25d_call_IV (linear slope),
skew convexity = (10d_put_IV - 2*ATM_IV + 10d_call_IV) / ATM_IV
= butterfly spread of IV across the smile.

High positive convexity = extreme tails priced richer than linear skew implies
(platinum/crystal skews, fat tail risk pricing).
Low/negative convexity = linear or concave skew (normal market, thin tails).

Signal intuition:
- Convexity spikes → market pricing crash/jump risk beyond normal skew
- Convexity collapse → complacency, tail hedges unwinding
- Cross-sectionally: highest convexity names = most tail risk priced → potential mean reversion
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime


TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_iv_at_moneyness(chain_df, current_price, target_moneyness, option_type='put'):
    """Get IV at a specific moneyness level.
    
    moneyness = strike / spot
    - 0.90 = 10% OTM put
    - 0.95 = 5% OTM put (~25 delta)
    - 1.00 = ATM
    - 1.05 = 5% OTM call (~25 delta)
    - 1.10 = 10% OTM call
    """
    target_strike = current_price * target_moneyness
    
    if option_type == 'put':
        candidates = chain_df[chain_df['strike'] < current_price]
    else:
        candidates = chain_df[chain_df['strike'] > current_price]
    
    if len(candidates) == 0:
        return np.nan
    
    idx = (candidates['strike'] - target_strike).abs().idxmin()
    row = candidates.loc[idx]
    return row['impliedVolatility'] if pd.notna(row['impliedVolatility']) else np.nan


def compute_skew_convexity(ticker_str):
    """Compute IV skew convexity metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Get valid expirations within 180 days, focus on 7-60 DTE for liquidity
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 7 <= dte <= 60:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            return None
        
        # Use nearest liquid expiration (monthly preferred)
        target_exp = valid_exps[0]
        exp_date, dte = target_exp
        exp_str = exp_date.strftime("%Y-%m-%d")
        
        try:
            chain = tq.option_chain(exp_str)
            calls = chain.calls
            puts = chain.puts
        except Exception:
            return None
        
        # Filter liquid options with valid IV
        for df in [calls, puts]:
            df['volume'] = df['volume'].fillna(0)
            df['openInterest'] = df['openInterest'].fillna(0)
        
        calls = calls[
            (calls['impliedVolatility'].notna()) &
            (calls['impliedVolatility'] > 0.01) &
            (calls['impliedVolatility'] < 3.0) &
            ((calls['volume'] > 10) | (calls['openInterest'] > 100))
        ].copy()
        
        puts = puts[
            (puts['impliedVolatility'].notna()) &
            (puts['impliedVolatility'] > 0.01) &
            (puts['impliedVolatility'] < 3.0) &
            ((puts['volume'] > 10) | (puts['openInterest'] > 100))
        ].copy()
        
        if len(calls) < 10 or len(puts) < 10:
            return None
        
        # Get IV at key moneyness levels
        # ATM
        atm_iv_put = get_iv_at_moneyness(puts, current_price, 1.00, 'put')
        atm_iv_call = get_iv_at_moneyness(calls, current_price, 1.00, 'call')
        atm_iv = np.nanmedian([atm_iv_put, atm_iv_call])
        
        if pd.isna(atm_iv) or atm_iv <= 0:
            return None
        
        # 25-delta (~5% OTM)
        put_25d = get_iv_at_moneyness(puts, current_price, 0.95, 'put')
        call_25d = get_iv_at_moneyness(calls, current_price, 1.05, 'call')
        
        # 10-delta (~10% OTM) - for convexity
        put_10d = get_iv_at_moneyness(puts, current_price, 0.90, 'put')
        call_10d = get_iv_at_moneyness(calls, current_price, 1.10, 'call')
        
        # 5-delta (~15% OTM) - for deep tail convexity
        put_5d = get_iv_at_moneyness(puts, current_price, 0.85, 'put')
        call_5d = get_iv_at_moneyness(calls, current_price, 1.15, 'call')
        
        if any(pd.isna(x) for x in [put_25d, call_25d, put_10d, call_10d, put_5d, call_5d]):
            return None
        
        # Standard skew (linear): 25d put - 25d call
        skew_25d = put_25d - call_25d
        
        # Skew convexity (butterfly): 10d_put - 2*ATM + 10d_call
        # Normalized by ATM IV for cross-sectional comparison
        skew_convexity_10d = (put_10d - 2 * atm_iv + call_10d) / atm_iv
        
        # Deep tail convexity: 5d_put - 2*ATM + 5d_call
        skew_convexity_5d = (put_5d - 2 * atm_iv + call_5d) / atm_iv
        
        # Skew slope (linear component): (25d_put - ATM) - (ATM - 25d_call)
        # = put_25d + call_25d - 2*ATM
        skew_slope = (put_25d + call_25d - 2 * atm_iv) / atm_iv
        
        # Tail convexity premium: convexity beyond what linear skew predicts
        # If skew were linear, 10d_put - call_10d should scale with 25d_put - call_25d
        # We measure the deviation
        predicted_10d_skew = skew_25d * (0.10 / 0.05)  # Linear extrapolation
        actual_10d_skew = put_10d - call_10d
        tail_convexity_premium = (actual_10d_skew - predicted_10d_skew) / atm_iv
        
        # Put/Call wing ratio: 10d_put / 10d_call (smile symmetry)
        wing_ratio = put_10d / call_10d if call_10d > 0 else np.inf
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'expiration': exp_str,
            'dte': dte,
            'atm_iv': round(atm_iv, 4),
            'put_25d_iv': round(put_25d, 4),
            'call_25d_iv': round(call_25d, 4),
            'put_10d_iv': round(put_10d, 4),
            'call_10d_iv': round(call_10d, 4),
            'put_5d_iv': round(put_5d, 4),
            'call_5d_iv': round(call_5d, 4),
            'skew_25d': round(skew_25d, 6),
            'skew_convexity_10d': round(skew_convexity_10d, 6),
            'skew_convexity_5d': round(skew_convexity_5d, 6),
            'skew_slope': round(skew_slope, 6),
            'tail_convexity_premium': round(tail_convexity_premium, 6),
            'wing_ratio': round(wing_ratio, 4) if np.isfinite(wing_ratio) else np.nan,
            'n_put_contracts': len(puts),
            'n_call_contracts': len(calls),
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 IV Skew Convexity (Butterfly Skew) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_skew_convexity(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}, {r['dte']} DTE, {r['expiration']}):")
        print(f"  ATM IV:              {r['atm_iv']:.4f}")
        print(f"  25d Put/Call IV:     {r['put_25d_iv']:.4f} / {r['call_25d_iv']:.4f}")
        print(f"  10d Put/Call IV:     {r['put_10d_iv']:.4f} / {r['call_10d_iv']:.4f}")
        print(f"  5d Put/Call IV:      {r['put_5d_iv']:.4f} / {r['call_5d_iv']:.4f}")
        print(f"  Skew (25d):          {r['skew_25d']:.6f}")
        print(f"  Convexity (10d):     {r['skew_convexity_10d']:.6f}")
        print(f"  Convexity (5d):      {r['skew_convexity_5d']:.6f}")
        print(f"  Skew Slope:          {r['skew_slope']:.6f}")
        print(f"  Tail Convexity Prem: {r['tail_convexity_premium']:.6f}")
        print(f"  Wing Ratio (10d):    {r['wing_ratio']:.4f}")
        print(f"  Contracts:           {r['n_put_contracts']}P / {r['n_call_contracts']}C")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_skew_convexity_latest.csv"
    
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")