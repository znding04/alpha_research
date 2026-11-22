#!/usr/bin/env python3
"""VRP Focus (alpha_49_vrp_focus) — Variance Risk Premium for 6 focus tickers.

Computes IV^2 - RV^2 where:
  IV = ATM implied volatility from options chain
  RV = 30-day realized volatility from historical close-to-close log returns

Classic equity premium signal: Positive VRP = options relatively expensive
(fear premium earned); Cross-sectionally, high VRP names have exhibited
different return characteristics.
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

# The 6 focus tickers from the alpha_research universe:
# AAPL, MSFT, GOOGL, AMZN (single names) + SPY, QQQ (index ETFs)
FOCUS_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "SPY", "QQQ"]


def compute_atm_iv(ticker_str):
    """Get ATM implied volatility from the options chain for a single ticker.

    Uses the nearest liquid expiration within a DTE range (14-60).
    ATM is defined as strikes within ±3% of the current price.
    Returns volume-weighted IV across calls+puts, or None on failure.
    """
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            return None, None

        expirations = list(tq.options)
        now = datetime.now()

        # Filter expirations within DTE range
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 14 <= dte <= 60:
                    valid_exps.append((d, dte, e))
            except ValueError:
                continue

        if not valid_exps:
            return None, current_price

        # Sort by DTE (nearest valid first), pick the first valid expiration
        valid_exps.sort(key=lambda x: x[1])
        target_exp, dte, target_str = valid_exps[0]

        chain = tq.option_chain(target_str)
        calls = chain.calls
        puts = chain.puts

        # Filter liquid options (volume > 10 or OI > 100 per leg)
        calls = calls[
            ((calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100))
        ].copy()
        puts = puts[
            ((puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100))
        ].copy()

        if len(calls) < 5 or len(puts) < 5:
            return None, current_price

        all_options = pd.concat([calls, puts], ignore_index=True)

        # Define moneyness range: strikes within 3% of spot
        moneyness_low = current_price * 0.97
        moneyness_high = current_price * 1.03
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low)
            & (all_options['strike'] <= moneyness_high)
        ].copy()

        if len(near_atm) == 0:
            # Fallback: any option with valid IV > 0.01
            near_atm = all_options[
                (all_options['impliedVolatility'].notna())
                & (all_options['impliedVolatility'] > 0.01)
                & (all_options['impliedVolatility'] < 3.0)
            ].copy()

        if len(near_atm) == 0:
            return None, current_price

        # Volume-weighted average IV
        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = round(
                (near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq,
                4,
            )
        else:
            atm_iv = round(near_atm['impliedVolatility'].median(), 4)

        return atm_iv, round(current_price, 2)

    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return None, None


def compute_realized_vol(ticker_str, lookback_days=30):
    """Compute 30-day annualized realized volatility from historical closes.

    Uses last (lookback_days + 15) calendar days of price history to ensure
    at least lookback_days of log returns, then takes the std of the most recent
    lookback_days annualized by sqrt(252).
    """
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


def compute_vrp_metrics(ticker_str, rv_lookback=30):
    """Compute VRP = IV^2 - RV^2 metrics for a single ticker.

    Returns a dict with all relevant fields, or None if computation fails.
    """
    atm_iv, current_price = compute_atm_iv(ticker_str)

    if atm_iv is None or pd.isna(atm_iv) or atm_iv <= 0:
        return None

    rv = compute_realized_vol(ticker_str, rv_lookback)
    if pd.isna(rv) or rv <= 0:
        return None

    # VRP = IV^2 - RV^2 (variance risk premium)
    iv_var = atm_iv ** 2
    rv_var = rv ** 2
    vrp = iv_var - rv_var

    # VRP in vol points (signed: positive if IV > RV)
    vrp_vol = np.sqrt(max(vrp, 0)) if vrp > 0 else -np.sqrt(abs(vrp))

    # VRP ratio
    vrp_ratio = iv_var / rv_var if rv_var > 0 else np.nan

    return {
        "ticker": ticker_str,
        "current_price": round(current_price, 2),
        "atm_iv": atm_iv,
        "realized_vol": round(rv, 4),
        "iv_variance": round(iv_var, 6),
        "rv_variance": round(rv_var, 6),
        "vrp_variance": round(vrp, 6),
        "vrp_vol_points": round(vrp_vol, 4),
        "vrp_ratio": round(vrp_ratio, 4),
    }


if __name__ == "__main__":
    print(
        f"\n📊 VRP Focus (alpha_49_vrp_focus) — "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    print("=" * 70)

    results = []
    for t in FOCUS_TICKERS:
        r = compute_vrp_metrics(t)
        if r:
            results.append(r)
            vrp_sign = "📈" if r["vrp_variance"] > 0 else "📉"
            print(
                f"\n{r['ticker']} (${r['current_price']}):"
            )
            print(f"  ATM IV (ann.):      {r['atm_iv']:.4f}")
            print(f"  Realized Vol (ann.): {r['realized_vol']:.4f}")
            print(f"  IV^2 - RV^2:        {r['vrp_variance']:.6f} {vrp_sign}")
            print(f"  VRP (vol pts):      {r['vrp_vol_points']:.4f}")
            print(f"  VRP Ratio (IV^2/RV^2): {r['vrp_ratio']:.4f}")

    if not results:
        print("No data collected.")
        sys.exit(1)

    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_focus_latest.csv"
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")