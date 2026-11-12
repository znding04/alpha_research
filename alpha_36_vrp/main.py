#!/usr/bin/env python3
"""Alpha 36 — VRP (Variance Risk Premium).

Signal: VRP = IV^2 − RV^2 where IV is ATM implied volatility from current option chain
and RV is 30-day annualized realized volatility from daily close-to-close log returns.

Interpretation:
  VRP > 0 → positive variance risk premium (IV^2 > RV^2) — vol is expensively priced,
              potential short-vol / underweight signal
  VRP < 0 → negative variance risk premium (IV^2 < RV^2) — vol is cheap,
              potential mean-reversion long / overweight signal

Cross-sectionally: rank tickers by VRP. Most positive = most complacent (overpriced vol).
Most negative = most fearful (underpriced vol).

Uses yfinance only — no paid APIs. Cross-section across 16 tickers from common/universe.py.
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

RV_WINDOW = 30       # realized volatility window (trading days)
ANNUALIZATION = np.sqrt(252)
TARGET_DTE = 30      # target DTE for IV selection
DTE_WINDOW = 10      # accept expiration within ±10 days of TARGET_DTE


def get_atm_iv(ticker_str):
    """Get ATM IV from expiration closest to TARGET_DTE within DTE_WINDOW."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None, None, None

        expirations = list(tq.options)
        now = datetime.now()
        best_exp = None
        best_dte = None
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d.date() - now.date()).days
                if 0 < dte <= 180 and abs(dte - TARGET_DTE) <= DTE_WINDOW:
                    if best_dte is None or abs(dte - TARGET_DTE) < abs(best_dte - TARGET_DTE):
                        best_exp = e
                        best_dte = dte
            except ValueError:
                continue

        if best_exp is None:
            return None, None, None

        chain = tq.option_chain(best_exp)
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        for df in (calls, puts):
            df['volume'] = df['volume'].fillna(0)
            df['openInterest'] = df['openInterest'].fillna(0)

        liquid = pd.concat([calls, puts], ignore_index=True)
        liquid = liquid[
            ((liquid['volume'] > 5) | (liquid['openInterest'] > 50)) &
            (liquid['impliedVolatility'].notna()) &
            (liquid['impliedVolatility'] > 0.05) &
            (liquid['impliedVolatility'] < 3.0) &
            (liquid['lastPrice'] > 0)
        ]

        if len(liquid) < 10:
            return None, None, None

        moneyness = liquid['strike'] / current_price
        atm_candidates = liquid[(moneyness >= 0.98) & (moneyness <= 1.02)]
        if len(atm_candidates) >= 3:
            atm_iv = float(atm_candidates['impliedVolatility'].median())
        else:
            valid = liquid[liquid['impliedVolatility'] > 0.05]
            if len(valid) == 0:
                return None, None, None
            idx = (valid['strike'] - current_price).abs().idxmin()
            atm_iv = float(valid.loc[idx, 'impliedVolatility'])

        return atm_iv, best_dte, current_price
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None, None, None


def get_realized_vol(ticker_str, window=RV_WINDOW):
    """Compute annualized realized volatility from daily close-to-close returns."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period="60d", interval="1d")
        if len(hist) < window + 2:
            return None
        close = hist['Close']
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < window:
            return None
        rv = float(log_ret.iloc[-window:].std() * ANNUALIZATION)
        return rv
    except Exception as e:
        print(f"  ⚠️ {ticker_str} RV: {e}")
        return None


def compute_vrp(ticker_str):
    """Compute VRP = IV^2 − RV^2 for a single ticker."""
    try:
        atm_iv, dte, current_price = get_atm_iv(ticker_str)
        if atm_iv is None:
            return None

        rv = get_realized_vol(ticker_str)
        if rv is None:
            return None

        iv_sq = atm_iv ** 2
        rv_sq = rv ** 2
        vrp = iv_sq - rv_sq

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2) if current_price else None,
            'dte': dte,
            'atm_iv': round(atm_iv, 4),
            'realized_vol': round(rv, 4),
            'iv_squared': round(iv_sq, 6),
            'rv_squared': round(rv_sq, 6),
            'vrp': round(vrp, 6),
            'vrp_bps': round(vrp * 10000, 2),  # in basis points of vol^2
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 VRP (Variance Risk Premium) — Alpha 36 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Signal: VRP = IV^2 − RV^2  (RV = {RV_WINDOW}d realized vol, IV from {TARGET_DTE}±{DTE_WINDOW}d DTE)")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_vrp(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   VRP > 0 → positive variance risk premium (IV^2 > RV^2, expensively priced vol)")
    print("   VRP < 0 → negative variance risk premium (IV^2 < RV^2, cheap vol)")

    os.makedirs("data", exist_ok=True)
    path = "data/vrp_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")