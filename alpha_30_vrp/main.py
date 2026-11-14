#!/usr/bin/env python3
"""VRP Signal (alpha_30_vrp) — Variance Risk Premium: ATM IV minus realized volatility.

Uses yfinance option chains for ATM IV and 20-day trailing realized vol.
Saves cross-sectional signal values to data/vrp_alpha_30.csv.
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


def get_nearest_exp(tq, min_dte=7, max_dte=60):
    """Get nearest valid expiration within DTE range."""
    try:
        exps = list(tq.options)
        now = datetime.now()
        valid = []
        for e in exps:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if min_dte <= dte <= max_dte:
                    valid.append((d, dte))
            except ValueError:
                continue
        valid.sort(key=lambda x: x[0])
        return valid[0][0].strftime("%Y-%m-%d") if valid else None
    except Exception:
        return None


def get_robust_atm_iv(tq, price, exp_str):
    """Get median ATM IV from option chain."""
    try:
        chain = tq.option_chain(exp_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.05) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()
        if len(df) < 10:
            return None
        moneyness = df['strike'] / price
        atm = df[(moneyness >= 0.98) & (moneyness <= 1.02)]
        if len(atm) >= 3:
            return atm['impliedVolatility'].median()
        else:
            vs = df[df['impliedVolatility'] > 0.05]
            if len(vs) == 0:
                return None
            idx = (vs['strike'] - price).abs().idxmin()
            return vs.loc[idx, 'impliedVolatility']
    except Exception:
        return None


def get_realized_vol(ticker, window=20):
    """Compute annualized realized volatility from daily closes."""
    try:
        hist = yf.Ticker(ticker).history(period="3mo", interval="1d")
        close = hist["Close"].dropna()
        if len(close) < window + 5:
            return None
        log_ret = np.log(close / close.shift(1)).dropna()
        rv = log_ret.iloc[-window:].std() * np.sqrt(252)
        return float(rv) if rv > 0 else None
    except Exception:
        return None


def compute_vrp_signal(ticker_str):
    """Compute VRP = ATM IV - realized vol for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price is None or price <= 0:
            return None

        exp_str = get_nearest_exp(tq)
        if exp_str is None:
            return None

        atm_iv = get_robust_atm_iv(tq, price, exp_str)
        if atm_iv is None:
            return None

        rv = get_realized_vol(ticker_str, window=20)
        if rv is None:
            return None

        vrp = atm_iv - rv
        return {
            'ticker': ticker_str,
            'current_price': round(price, 2),
            'atm_iv': round(atm_iv, 4),
            'realized_vol': round(rv, 4),
            'vrp': round(vrp, 4),
            'expiration': exp_str,
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 VRP Signal (alpha_30_vrp) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_vrp_signal(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   vrp > 0 → IV > RV (vol premium priced in)")
    print("   vrp < 0 → RV > IV (vol cheap relative to history)")

    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_alpha_30.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")