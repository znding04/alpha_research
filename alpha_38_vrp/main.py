#!/usr/bin/env python3
"""Alpha 38 — VRP (Variance Risk Premium).

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
            # Fallback: nearest expiration with DTE > 7
            valid = []
            for e in expirations:
                try:
                    d = datetime.strptime(e, "%Y-%m-%d")
                    dte = (d.date() - now.date()).days
                    if 7 < dte <= 180:
                        valid.append((dte, e))
                except ValueError:
                    continue
            if not valid:
                return None, None, None
            valid.sort()
            best_exp = valid[0][1]
            best_dte = valid[0][0]

        chain = tq.option_chain(best_exp)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # Fix dtypes: volume/OI are numpy int64, comparison fails on NaN/inf
        df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)

        # Filter: liquid + valid IV + reasonable IV
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()

        if len(df) < 10:
            return None, None, None

        # ATM IV: median of strikes within ±2% moneyness with IV > 5%
        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]

        if len(atm_candidates) >= 3:
            atm_iv = atm_candidates['impliedVolatility'].median()
        else:
            valid_strikes = df[df['impliedVolatility'] > 0.05]
            if len(valid_strikes) == 0:
                return None, None, None
            atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
            atm_iv = valid_strikes.loc[atm_idx, 'impliedVolatility']

        return float(atm_iv), float(current_price), int(best_dte)

    except Exception as e:
        print(f"  ⚠️ {ticker_str} (get_atm_iv): {e}")
        return None, None, None


def get_realized_vol(ticker_str, window=RV_WINDOW):
    """Compute annualized realized volatility from daily close-to-close log returns."""
    try:
        tq = yf.Ticker(ticker_str)
        # Fetch enough history for window + buffer
        hist = tq.history(period=f"{window + 20}d", interval="1d")
        if len(hist) < window + 5:
            return None

        close = hist['Close'].dropna()
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < window:
            return None

        rv = log_ret.iloc[-window:].std() * ANNUALIZATION
        return float(rv)
    except Exception as e:
        print(f"  ⚠️ {ticker_str} (get_realized_vol): {e}")
        return None


def compute_vrp(ticker_str):
    """Compute VRP = IV^2 - RV^2 for a single ticker."""
    atm_iv, price, dte = get_atm_iv(ticker_str)
    if atm_iv is None:
        return None

    rv = get_realized_vol(ticker_str)
    if rv is None:
        return None

    vrp = atm_iv ** 2 - rv ** 2

    return {
        'ticker': ticker_str,
        'atm_iv': round(atm_iv, 4),
        'realized_vol': round(rv, 4),
        'vrp': round(vrp, 6),
        'price': round(price, 2),
        'dte': dte,
    }


if __name__ == "__main__":
    print(f"\n🔍 VRP Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
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
    # Sort by VRP (most positive first = most overpriced vol)
    df = df.sort_values('vrp', ascending=False).reset_index(drop=True)
    print(df.to_string(index=False))

    print("\n💡 Interpretation:")
    print("   VRP > 0 → IV^2 > RV^2 (vol overpriced, short-vol signal)")
    print("   VRP < 0 → IV^2 < RV^2 (vol underpriced, long-vol signal)")

    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total tickers: {len(df)}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")