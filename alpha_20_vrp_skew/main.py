#!/usr/bin/env python3
"""VRP Skew alpha signal.

Measures the asymmetry of variance risk premium between puts and calls.
VRP = IV^2 - RV^2. Put VRP uses OTM put IV; Call VRP uses OTM call IV.
Signal = Put VRP - Call VRP (positive = put VRP premium / crash hedging demand).

Cross-sectional signal: rank tickers by VRP skew; long low VRP skew (call premium), short high VRP skew (put premium).
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

from common.universe import TICKERS


def get_realized_vol(ticker_str, lookback_days=30):
    """Compute realized volatility from daily close prices."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{lookback_days + 5}d", interval="1d")
        if len(hist) < lookback_days:
            return np.nan
        closes = hist['Close'].dropna()
        log_returns = np.log(closes / closes.shift(1)).dropna()
        rv = log_returns.std() * np.sqrt(252)
        return float(rv)
    except Exception:
        return np.nan


def get_otm_iv(chain_df, current_price, option_type, moneyness_target=0.05):
    """Get IV for OTM option at target moneyness.
    
    For puts: OTM = strike < spot, target strike = spot * (1 - moneyness_target)
    For calls: OTM = strike > spot, target strike = spot * (1 + moneyness_target)
    """
    if option_type == 'put':
        target_strike = current_price * (1 - moneyness_target)
        candidates = chain_df[(chain_df['strike'] < current_price) & 
                              (chain_df['impliedVolatility'].notna()) &
                              (chain_df['impliedVolatility'] > 0.01) &
                              (chain_df['lastPrice'] > 0)]
    else:
        target_strike = current_price * (1 + moneyness_target)
        candidates = chain_df[(chain_df['strike'] > current_price) & 
                              (chain_df['impliedVolatility'].notna()) &
                              (chain_df['impliedVolatility'] > 0.01) &
                              (chain_df['lastPrice'] > 0)]
    
    if len(candidates) == 0:
        return np.nan
    
    # Find closest strike to target
    idx = (candidates['strike'] - target_strike).abs().idxmin()
    return candidates.loc[idx, 'impliedVolatility']


def compute_vrp_skew(ticker_str, rv_lookback=30, moneyness=0.05, max_dte=45):
    """Compute VRP skew for a single ticker.
    
    Args:
        ticker_str: Ticker symbol
        rv_lookback: Days for realized vol estimation
        moneyness: OTM moneyness for IV selection (0.05 = 5% OTM)
        max_dte: Maximum days to expiration to consider
    
    Returns:
        Dict with VRP skew metrics or None
    """
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        
        # Get realized volatility
        rv = get_realized_vol(ticker_str, rv_lookback)
        if pd.isna(rv):
            return None
        rv_sq = rv ** 2
        
        # Get valid expirations
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 2 < dte <= max_dte:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            return None
        
        vrp_skews = []
        vrp_puts = []
        vrp_calls = []
        
        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                df = pd.concat([chain.calls, chain.puts], ignore_index=True)
                
                # Filter liquid options
                df['volume'] = df['volume'].fillna(0)
                df['openInterest'] = df['openInterest'].fillna(0)
                liquid = df[((df['volume'] > 10) | (df['openInterest'] > 100))].copy()
                
                if len(liquid) < 20:
                    continue
                
                # Get OTM put IV (~5% OTM)
                put_iv = get_otm_iv(liquid, current_price, 'put', moneyness)
                # Get OTM call IV (~5% OTM)
                call_iv = get_otm_iv(liquid, current_price, 'call', moneyness)
                
                if pd.isna(put_iv) or pd.isna(call_iv):
                    continue
                
                # VRP = IV^2 - RV^2
                put_vrp = put_iv ** 2 - rv_sq
                call_vrp = call_iv ** 2 - rv_sq
                vrp_skew = put_vrp - call_vrp
                
                vrp_skews.append(vrp_skew)
                vrp_puts.append(put_vrp)
                vrp_calls.append(call_vrp)
                
            except Exception:
                continue
        
        if not vrp_skews:
            return None
        
        # Aggregate across expirations (mean)
        mean_vrp_skew = np.nanmean(vrp_skews)
        mean_put_vrp = np.nanmean(vrp_puts)
        mean_call_vrp = np.nanmean(vrp_calls)
        
        # Also get near-term (shortest DTE) values
        near_idx = 0
        near_vrp_skew = vrp_skews[near_idx] if vrp_skews else np.nan
        near_put_vrp = vrp_puts[near_idx] if vrp_puts else np.nan
        near_call_vrp = vrp_calls[near_idx] if vrp_calls else np.nan
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'rv_annualized': round(rv, 4),
            'near_vrp_skew': round(near_vrp_skew, 6),
            'near_put_vrp': round(near_put_vrp, 6),
            'near_call_vrp': round(near_call_vrp, 6),
            'mean_vrp_skew': round(mean_vrp_skew, 6),
            'mean_put_vrp': round(mean_put_vrp, 6),
            'mean_call_vrp': round(mean_call_vrp, 6),
            'n_expirations': len(vrp_skews),
        }
        
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📈 VRP Skew Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_vrp_skew(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  RV (annualized):      {r['rv_annualized']:.4f}")
        print(f"  Near Put VRP:         {r['near_put_vrp']:.6f}")
        print(f"  Near Call VRP:        {r['near_call_vrp']:.6f}")
        print(f"  Near VRP Skew:        {r['near_vrp_skew']:.6f}")
        print(f"  Mean VRP Skew:        {r['mean_vrp_skew']:.6f}")
        print(f"  Expirations used:     {r['n_expirations']}")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_skew_latest.csv"
    
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")