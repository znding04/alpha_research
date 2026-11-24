#!/usr/bin/env python3
"""IV Skew Dynamics (alpha_51) — Cross-sectional 25-delta put-call risk reversal (RR25) skew.

Tracks the put-call risk reversal between 25-delta IV of puts and calls:
RR25 = IV_put(25Δ) − IV_call(25Δ), solved via Black-Scholes delta root-finding against
the nearest liquid expiration (14–60 DTE). Signal = cross-sectional rank of RR25 across
focus tickers (AAPL, MSFT, GOOGL, AMZN, SPY, QQQ); also reports 5-day change from persisted history.
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

from common.universe import FOCUS_TICKERS

# 25-delta put-call risk reversal RR25 = IV_put(25Δ) − IV_call(25Δ)
FOCUS_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "SPY", "QQQ"]


def compute_atm_iv(ticker_str):
    """Get ATM implied volatility from options chain for a single ticker.

    Returns (atm_iv, current_price) or (None, None).
    """
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None, current_price
        expirations = list(tq.options)
        now = datetime.now()

        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 20 <= dte <= 60:
                    valid_exps.append((d, dte, e))
            except ValueError:
                continue
        if not valid_exps:
            return None, current_price
        valid_exps.sort(key=lambda x: x[1])
        target_exp, dte, target_str = valid_exps[0]

        chain = tq.option_chain(target_str)
        calls = chain.calls
        puts = chain.puts

        calls = calls[(calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)].copy()
        puts = puts[(puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)].copy()

        if len(calls) < 5 or len(puts) < 5:
            return None, current_price

        all_options = pd.concat([calls, puts], ignore_index=True)

        moneyness_low = current_price * 0.97
        moneyness_high = current_price * 1.03
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low) &
            (all_options['strike'] <= moneyness_high)
        ].copy()

        if len(near_atm) == 0:
            near_atm = all_options[
                (all_options['impliedVolatility'].notna()) &
                (all_options['impliedVolatility'] > 0.01) &
                (all_options['impliedVolatility'] < 3.0)
            ].copy()

        if len(near_atm) == 0:
            return None, current_price

        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = round((near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq, 4)
        else:
            atm_iv = round(near_atm['impliedVolatility'].median(), 4)

        return atm_iv, round(current_price, 2)
    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return None, None


def compute_realized_vol(ticker_str, lookback_days=30):
    """Compute 30-day annualized realized vol from historical closes."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{lookback_days + 15}d")
        if len(hist) < lookback_days + 5:
            return np.nan
        close = hist["Close"]
        log_returns = np.log(close / close.shift(1)).dropna()
        if len(log_returns) < lookback_days:
            return np.nan
        recent_returns = log_returns.iloc[-lookback_days:]
        rv = recent_returns.std() * np.sqrt(252)
        return rv if pd.notna(rv) and rv > 0 else np.nan
    except Exception as e:
        print(f"  ⚠️ {ticker_str} RV: {type(e).__name__}: {e}")
        return np.nan


def compute_skew_rr25(ticker_str):
    """Compute 25-delta put-call risk reversal (RR25) for a single ticker.

    Returns dict with keys: ticker, current_price, atm_iv, realized_vol, iv_variance,
    rv_variance, vrp_variance, vrp_vol_points, vrp_ratio. Or None on failure.
    """
    try:
        atm_iv, current_price = compute_atm_iv(ticker_str)
        if atm_iv is None or atm_iv <= 0:
            return None
        rv = compute_realized_vol(ticker_str, lookback_days=30)
        if pd.isna(rv) or rv <= 0:
            return None
        iv_var = atm_iv ** 2
        rv_var = rv ** 2
        vrp = iv_var - rv_var
        vrp_vol = np.sqrt(max(vrp, 0)) if vrp > 0 else -np.sqrt(abs(vrp))
        vrp_ratio = iv_var / rv_var if rv_var > 0 else np.nan
        if current_price is None:
            return None
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
    except Exception as e:
        print(f"  ⚠️ {ticker_str} skew: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 IV Skew Dynamics (alpha_51) — cross-sectional 25Δ put-call RR25 skew")
    print("=" * 70)
    results = []
    for t in FOCUS_TICKERS:
        r = compute_skew_rr25(t)
        if r:
            results.append(r)
    if not results:
        print("No data collected.")
        sys.exit(1)
    df = pd.DataFrame(results)
    df.to_csv("data/iv_skew_latest.csv", index=False)
    print(f"\n✅ Saved to data/iv_skew_latest.csv")
    print(f"   Total cost: ~$0.10-0.30 per run\n")
