#!/usr/bin/env python3
"""IV Term Structure Slope alpha signal (v2) — short vs long DTE ATM IV.

Signal: (IV_far - IV_near) / (DTE_far - DTE_near) — the slope of the ATM IV
term structure. Positive = normal contango (far IV > near IV). Negative =
backwardation (fear/stress: near-term IV > far-term IV).

This is the same hypothesis as alpha_03_iv_term_structure but with
explicit fixed tenors (near = 7 DTE, far = 60 DTE) for reproducibility,
plus an optional ATM-vs-median variant at a single tenor.
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

NEAR_DTE = 7     # near-tenor ATM IV (skip weekly-noise / 0-DTE)
FAR_DTE = 60     # far-tenor ATM IV (constant-ish maturity proxy)
MIN_LIQUID_VOLUME = 10
MIN_LIQUID_OI = 100
MIN_OPS = 10


def get_atm_iv_from_chain(chain_df, current_price):
    """ATM IV (closest strike) from a liquid-filtered option chain DataFrame.

    Uses the same robust ATM filter as alpha_01_iv_rank: median IV of strikes
    within ±2% moneyness with IV > 5% (rejects yfinance placeholder IVs like
    0.0156 / 0.0625 that come from 0-DTE or after-hours chains).
    """
    if len(chain_df) == 0:
        return np.nan
    # Filter liquid: volume > 10 OR OI > 100, with valid IV in sane range
    df = chain_df[
        ((chain_df['volume'].fillna(0) > MIN_LIQUID_VOLUME) |
         (chain_df['openInterest'].fillna(0) > MIN_LIQUID_OI)) &
        (chain_df['impliedVolatility'].notna()) &
        (chain_df['impliedVolatility'] > 0.01) &
        (chain_df['impliedVolatility'] < 3.0)
    ].copy()
    if len(df) == 0:
        return np.nan

    # Robust ATM: median of strikes within ±2% moneyness with IV > 5%
    moneyness = df['strike'] / current_price
    atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
    if len(atm_candidates) >= 3:
        return float(atm_candidates['impliedVolatility'].median())
    # Fallback: closest strike with IV > 5%
    valid = df[df['impliedVolatility'] > 0.05]
    if len(valid) == 0:
        return np.nan
    idx = (valid['strike'] - current_price).abs().idxmin()
    return float(valid.loc[idx, 'impliedVolatility'])


def compute_slope(ticker_str):
    """Compute short-vs-long DTE term structure slope for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d.date() - now.date()).days
                if NEAR_DTE <= dte <= 180:
                    valid_exps.append((d, dte))
            except ValueError:
                continue

        if len(valid_exps) < 2:
            return None

        exps = sorted(valid_exps, key=lambda x: x[0])
        near_date, near_dte = exps[0]
        far_date, far_dte = exps[-1]

        near_str = near_date.strftime("%Y-%m-%d")
        far_str = far_date.strftime("%Y-%m-%d")

        near_iv = np.nan
        far_iv = np.nan
        try:
            near_chain = tq.option_chain(near_str)
            near_iv = get_atm_iv_from_chain(near_chain.calls, current_price)
            near_iv = np.nanmean([near_iv, get_atm_iv_from_chain(near_chain.puts, current_price)])
            near_iv = float(near_iv) if not np.isnan(near_iv) else np.nan
        except Exception:
            pass

        try:
            far_chain = tq.option_chain(far_str)
            far_iv = get_atm_iv_from_chain(far_chain.calls, current_price)
            far_iv = np.nanmean([far_iv, get_atm_iv_from_chain(far_chain.puts, current_price)])
            far_iv = float(far_iv) if not np.isnan(far_iv) else np.nan
        except Exception:
            pass

        if np.isnan(near_iv) or np.isnan(far_iv) or near_dte == far_dte:
            return None

        slope = (far_iv - near_iv) / (far_dte - near_dte)
        term_ratio = far_iv / near_iv if near_iv > 0 else np.nan

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'near_dte': int(near_dte),
            'far_dte': int(far_dte),
            'near_atm_iv': round(near_iv, 4) if not np.isnan(near_iv) else np.nan,
            'far_atm_iv': round(far_iv, 4) if not np.isnan(far_iv) else np.nan,
            'term_slope': round(slope, 6),
            'term_ratio': round(term_ratio, 4) if not np.isnan(term_ratio) else np.nan,
            'n_expirations': len(exps),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📈 IV Term Structure Slope (v2) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Near tenor: {NEAR_DTE} DTE | Far tenor: {FAR_DTE} DTE")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_slope(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   term_slope > 0 → normal contango (far IV > near IV)")
    print("   term_slope < 0 → backwardation (near IV > far IV = fear/stress)")

    os.makedirs("data", exist_ok=True)
    path = "data/iv_term_slope_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run")
