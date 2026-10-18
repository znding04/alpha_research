#!/usr/bin/env python3
"""VRP (Variance Risk Premium) alpha signal.

Computes IV^2 - RV^2 where IV is ATM implied volatility from options
and RV is realized volatility from historical returns.
Signal = VRP level and VRP change predict forward equity returns.

Classic equity premium: Positive VRP = options expensive (fear) → earn premium by selling vol.
Cross-sectionally: High VRP tickers → higher expected returns.
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


def compute_atm_iv(ticker_str, target_dte_range=(14, 60)):
    """Get ATM IV from nearest liquid expiration within target DTE range."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None, None
        
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if target_dte_range[0] <= dte <= target_dte_range[1]:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            return None, current_price
        
        # Use nearest valid expiration
        target_exp, dte = valid_exps[0]
        target_str = target_exp.strftime("%Y-%m-%d")
        
        chain = tq.option_chain(target_str)
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
            return None, current_price
        
        # Find ATM strike - use most liquid strike near ATM to avoid zero-IV issues
        all_options = pd.concat([calls, puts], ignore_index=True)
        
        # Define moneyness range: strikes within 5% of spot
        moneyness_low = current_price * 0.95
        moneyness_high = current_price * 1.05
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low) & 
            (all_options['strike'] <= moneyness_high)
        ].copy()
        
        if len(near_atm) == 0:
            return None, current_price
        
        # Filter for liquid options with valid IV > 0.01 (1%)
        near_atm = near_atm[
            (near_atm['volume'].fillna(0) > 10) | (near_atm['openInterest'].fillna(0) > 100)
        ].copy()
        near_atm = near_atm[
            (near_atm['impliedVolatility'].notna()) & 
            (near_atm['impliedVolatility'] > 0.01)
        ].copy()
        
        if len(near_atm) == 0:
            return None, current_price
        
        # Use the most liquid option's IV, or median IV of liquid near-ATM options
        # Weight by volume + OI
        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        # Weighted average IV by liquidity
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = (near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq
        else:
            atm_iv = near_atm['impliedVolatility'].median()
        
        return atm_iv, current_price
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return None, None


def compute_realized_vol(ticker_str, lookback_days=30):
    """Compute realized volatility from historical returns."""
    try:
        tq = yf.Ticker(ticker_str)
        # Get extra days for weekends/holidays
        hist = tq.history(period=f"{lookback_days + 15}d")
        if len(hist) < lookback_days + 5:
            return np.nan
        
        # Daily log returns
        close = hist['Close']
        log_returns = np.log(close / close.shift(1)).dropna()
        
        if len(log_returns) < lookback_days:
            return np.nan
        
        # Use last `lookback_days` returns
        recent_returns = log_returns.iloc[-lookback_days:]
        
        # Annualized realized volatility (252 trading days)
        rv = recent_returns.std() * np.sqrt(252)
        return rv if pd.notna(rv) and rv > 0 else np.nan
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str} RV: {type(e).__name__}: {e}")
        return np.nan


def compute_vrp_metrics(ticker_str, rv_lookback=30):
    """Compute VRP metrics for a single ticker."""
    # Get ATM IV (near-term)
    atm_iv, current_price = compute_atm_iv(ticker_str)
    
    if atm_iv is None or pd.isna(atm_iv) or atm_iv <= 0:
        return None
    
    # Get realized volatility
    rv = compute_realized_vol(ticker_str, rv_lookback)
    
    if pd.isna(rv) or rv <= 0:
        return None
    
    # VRP = IV^2 - RV^2 (variance risk premium)
    iv_var = atm_iv ** 2
    rv_var = rv ** 2
    vrp = iv_var - rv_var
    
    # VRP as annualized vol points (sqrt of variance difference)
    # Positive = IV > RV = options expensive
    vrp_vol = np.sqrt(max(vrp, 0)) if vrp > 0 else -np.sqrt(abs(vrp))
    
    # Also compute VRP ratio
    vrp_ratio = iv_var / rv_var if rv_var > 0 else np.nan
    
    return {
        'ticker': ticker_str,
        'current_price': round(current_price, 2),
        'atm_iv': round(atm_iv, 4),
        'realized_vol': round(rv, 4),
        'iv_variance': round(iv_var, 6),
        'rv_variance': round(rv_var, 6),
        'vrp_variance': round(vrp, 6),
        'vrp_vol_points': round(vrp_vol, 4),
        'vrp_ratio': round(vrp_ratio, 4),
    }


if __name__ == "__main__":
    print(f"\n📊 VRP (Variance Risk Premium) Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_vrp_metrics(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        vrp_sign = "📈" if r['vrp_variance'] > 0 else "📉"
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  ATM IV (ann.):      {r['atm_iv']:.4f}")
        print(f"  Realized Vol (ann.): {r['realized_vol']:.4f}")
        print(f"  IV² - RV²:          {r['vrp_variance']:.6f} {vrp_sign}")
        print(f"  VRP (vol pts):      {r['vrp_vol_points']:.4f}")
        print(f"  VRP Ratio (IV²/RV²): {r['vrp_ratio']:.4f}")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_latest.csv"
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")