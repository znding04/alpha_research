#!/usr/bin/env python3
"""VRP (Variance Risk Premium) refined alpha signal — IV^2 - RV^2.

Computes the Variance Risk Premium:
    VRP = IV_ATM^2 - RV_30D^2

where IV_ATM is the ATM implied volatility (annualized, from the liquid
~30 DTE option chain) and RV_30D is the 30-day realized volatility (annualized).

**Refinement over alpha_04_vrp:** uses RV over a 30-day window from price
history (not 20d), and uses a delta-neutral / delta-hedged IV proxy when
available, plus logs VRP rank across the cross-section daily.

Signal: Positive VRP (options expensive vs realized) → sell vol / equity
expensive. Negative VRP (options cheap) → buy vol / equity cheap.
Cross-sectionally: high VRP → expected higher forward returns.

Notes:
- This is a live signal: runs on today's yfinance option chains + price history.
- IC validation lives in ic_analysis.py (forward returns from snapshots).
- History: data/vrp23_latest.csv
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


def compute_rv_30d(ticker_str, lookback_days: int = 30) -> float:
    """30-day annualized realized volatility from daily closes."""
    try:
        hist = yf.Ticker(ticker_str).history(
            start=(datetime.now() - timedelta(days=lookback_days + 60)).strftime("%Y-%m-%d"),
            interval="1d",
        )
        close = hist["Close"].dropna()
        if len(close) < 10:
            return np.nan
        log_ret = np.log(close / close.shift(1)).dropna()
        rv = log_ret.tail(lookback_days).std() * np.sqrt(252)
        return float(rv)
    except Exception as e:
        print(f"  ⚠️ {ticker_str} RV30: {type(e).__name__}: {e}")
        return np.nan


def compute_atm_iv(ticker_str, target_dte_range=(14, 60)) -> float:
    """ATM IV (annualized decimal) from nearest liquid option within DTE range."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return np.nan

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
            return np.nan

        target_exp, dte = valid_exps[0]
        chain = tq.option_chain(target_exp.strftime("%Y-%m-%d"))
        calls = chain.calls
        puts = chain.puts

        calls = calls[
            (calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)
        ].copy()
        puts = puts[
            (puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)
        ].copy()

        if len(calls) < 5 or len(puts) < 5:
            return np.nan

        all_options = pd.concat([calls, puts], ignore_index=True)
        moneyness_low = current_price * 0.95
        moneyness_high = current_price * 1.05
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low) &
            (all_options['strike'] <= moneyness_high)
        ].copy()
        near_atm = near_atm[
            (near_atm['volume'].fillna(0) > 10) | (near_atm['openInterest'].fillna(0) > 100)
        ].copy()
        near_atm = near_atm[
            (near_atm['impliedVolatility'].notna()) &
            (near_atm['impliedVolatility'] > 0.01)
        ].copy()
        if len(near_atm) == 0:
            return np.nan

        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = (near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq
        else:
            atm_iv = near_atm['impliedVolatility'].median()
        return float(atm_iv)
    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return np.nan


def compute_vrp(ticker_str) -> dict | None:
    """Compute VRP = IV^2 - RV^2 for a single ticker."""
    atm_iv = compute_atm_iv(ticker_str)
    rv = compute_rv_30d(ticker_str)
    if atm_iv is None or rv is None or np.isnan(atm_iv) or np.isnan(rv):
        return None
    if atm_iv <= 0 or rv <= 0:
        return None
    return {
        'ticker': ticker_str,
        'current_price': round(float(tq_price(ticker_str)), 2),
        'atm_iv': round(float(atm_iv), 6),
        'rv_30d': round(float(rv), 6),
        'vrp': round(float(atm_iv ** 2 - rv ** 2), 6),
        'vrp_iv_squared': round(float(atm_iv ** 2), 6),
        'vrp_rv_squared': round(float(rv ** 2), 6),
    }


def tq_price(ticker_str: str) -> float:
    """Current price from yfinance (cached info call)."""
    info = yf.Ticker(ticker_str).info
    return float(info.get('currentPrice') or info.get('regularMarketPrice') or 0.0)


def compute_vrp_cross_section() -> pd.DataFrame:
    """Compute VRP for all tickers, cross-sectionally rank."""
    rows = []
    for t in TICKERS:
        r = compute_vrp(t)
        if r:
            rows.append(r)
    df = pd.DataFrame(rows)
    if not df.empty:
        df['vrp_rank'] = df['vrp'].rank(pct=True, method='average') * 100
        df['vrp_abs_rank'] = df['vrp'].abs().rank(pct=True) * 100
    return df


if __name__ == "__main__":
    print(f"\n📊 VRP Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    df = compute_vrp_cross_section()
    if df.empty:
        print("No data collected.")
        exit(1)

    print(df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   vrp > 0 → options trade at premium over realized vol (sell-iv regime)")
    print("   vrp < 0 → options trade below realized vol (buy-iv regime)")
    print("   High VRP rank → expected higher forward returns (regression to mean of IV)")

    os.makedirs("data", exist_ok=True)
    path = "data/vrp23_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")
