#!/usr/bin/env python3
"""VRP (Variance Risk Premium) alpha signal — cross-sectional, 6-ticker universe.

Computes IV^2 - RV^2 where IV is ATM implied volatility from options and
RV is realized volatility from historical returns.

Classic equity premium: Positive VRP = options expensive (fear) → expected
higher forward returns cross-sectionally. Signal = cross-sectionally ranked
VRP variance points.

Universe: AAPL, SPY, QQQ, MSFT, GOOGL, AMZN (yfinance option chains + price history).
No paid APIs required.
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

# Restricted universe per task: cross-sectional across 6 tickers only
TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]

RV_LOOKBACK = 30  # trading days for realized vol
DTE_RANGE = (14, 60)  # target expiration window for ATM IV


def compute_atm_iv(ticker_str):
    """ATM implied volatility from nearest liquid expiration within DTE range."""
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
                if DTE_RANGE[0] <= dte <= DTE_RANGE[1]:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        if not valid_exps:
            return None, current_price

        target_exp, dte = valid_exps[0]
        target_str = target_exp.strftime("%Y-%m-%d")

        chain = tq.option_chain(target_str)
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        def liq_filter(df):
            return df[((df['volume'].fillna(0) > 10) | (df['openInterest'].fillna(0) > 100))].copy()

        calls = liq_filter(calls)
        puts = liq_filter(puts)
        if len(calls) < 5 or len(puts) < 5:
            return None, current_price

        all_opts = pd.concat([calls, puts], ignore_index=True)
        lo = current_price * 0.95
        hi = current_price * 1.05
        near_atm = all_opts[(all_opts['strike'] >= lo) & (all_opts['strike'] <= hi)].copy()
        if len(near_atm) == 0:
            return None, current_price

        near_atm = near_atm[
            (near_atm['impliedVolatility'].notna()) &
            (near_atm['impliedVolatility'] > 0.01) &
            (near_atm['impliedVolatility'] < 3.0)
        ].copy()
        if len(near_atm) == 0:
            return None, current_price

        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = float((near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq)
        else:
            atm_iv = float(near_atm['impliedVolatility'].median())

        return atm_iv, current_price

    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return None, None


def compute_realized_vol(ticker_str, lookback_days=RV_LOOKBACK):
    """Annualized realized volatility from `lookback_days` of daily log returns."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{lookback_days + 20}d")
        if len(hist) < lookback_days + 5:
            return np.nan
        close = hist['Close']
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < lookback_days:
            return np.nan
        recent = log_ret.iloc[-lookback_days:]
        rv = float(recent.std() * np.sqrt(252))
        return rv if pd.notna(rv) and rv > 0 else np.nan
    except Exception as e:
        print(f"  ⚠️ {ticker_str} RV: {type(e).__name__}: {e}")
        return np.nan


def compute_vrp(ticker_str):
    """Compute VRP metrics for a single ticker."""
    atm_iv, price = compute_atm_iv(ticker_str)
    if atm_iv is None or pd.isna(atm_iv) or atm_iv <= 0:
        return None

    rv = compute_realized_vol(ticker_str)
    if pd.isna(rv) or rv <= 0:
        return None

    iv_var = atm_iv ** 2
    rv_var = rv ** 2
    vrp_var = iv_var - rv_var

    # VRP in vol-points form, preserving sign
    vrp_vol = np.sqrt(max(vrp_var, 0)) if vrp_var > 0 else -np.sqrt(abs(vrp_var))
    vrp_ratio = iv_var / rv_var if rv_var > 0 else np.nan

    return {
        'ticker': ticker_str,
        'current_price': round(price, 2),
        'atm_iv': round(atm_iv, 4),
        'realized_vol': round(rv, 4),
        'iv_variance': round(iv_var, 6),
        'rv_variance': round(rv_var, 6),
        'vrp_variance': round(vrp_var, 6),
        'vrp_vol_points': round(vrp_vol, 4),
        'vrp_ratio': round(vrp_ratio, 4),
    }


if __name__ == "__main__":
    print(f"\n📊 VRP (Variance Risk Premium) — alpha_33 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print(f"Universe: {', '.join(TICKERS)} | RV lookback: {RV_LOOKBACK}d | DTE: {DTE_RANGE[0]}-{DTE_RANGE[1]}")

    results = []
    for t in TICKERS:
        r = compute_vrp(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        sys.exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    # Cross-sectional ranking: higher VRP → richer options → higher expected return
    df['vrp_cross_rank'] = df['vrp_variance'].rank(ascending=False)
    print("\nCross-sectional VRP rank (1 = richest options / strongest signal):")
    print(df[['ticker', 'vrp_variance', 'vrp_vol_points', 'vrp_cross_rank']].to_string(index=False))

    os.makedirs("data", exist_ok=True)
    path = "data/vrp_alpha_33_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Mean VRP variance: {df['vrp_variance'].mean():.6f} | Median: {df['vrp_variance'].median():.6f}\n")
