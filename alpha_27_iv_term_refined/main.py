#!/usr/bin/env python3
"""IV Term Structure Slope (Refined) — short vs. long DTE ATM IV slope.

Signal: normalized slope of ATM IV term structure between two fixed tenors.
  slope_norm = (IV_far - IV_near) / IV_near  (percentage slope)

Interpretation:
  slope_norm > 0  → normal contango (far IV > near IV, calm)
  slope_norm < 0  → backwardation (near IV > far IV, fear/stress)

Cross-sectionally: rank tickers by slope_norm. Most backwardated
(negative) = highest stress = potential mean-reversion long.
Most contango (positive) = most complacent = potential short/underweight.

This is a live-snapshot signal using yfinance chains at two fixed tenors:
  NEAR_DTE = 7  (skips 0-DTE weekly noise)
  FAR_DTE = 49  (captures medium-term vol expectations)

Key differences from alpha_03/25/alpha_25:
  - Uses fixed DTE windows (±5 days) for reproducibility
  - Normalized slope (pct) for cross-ticker comparability
  - Simpler liquidity filter (volume > 5 OR OI > 50)
  - Uses farthest available expiration as baseline when exact not found
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

NEAR_DTE = 7      # near-tenor target DTE (skip weekly 0-DTE noise)
FAR_DTE = 49      # far-tenor target DTE (max available in yfinance)
MIN_LIQUID_VOLUME = 5
MIN_LIQUID_OI = 50
MIN_OPS = 5


def find_exp_by_dte(tq, target_dte, window=5):
    """Find the expiration closest to target_dte (within ±window days)."""
    try:
        expirations = list(tq.options)
    except Exception:
        return None, None
    now = datetime.now()
    best = None
    best_dte = None
    for e in expirations:
        try:
            d = datetime.strptime(e, "%Y-%m-%d")
            dte = (d.date() - now.date()).days
            if dte > 0 and abs(dte - target_dte) <= window:
                if best is None or abs(dte - target_dte) < abs(best_dte - target_dte):
                    best = e
                    best_dte = dte
        except ValueError:
            continue
    return best, best_dte


def get_farthest_expiration(tq):
    """Get the farthest valid expiration (for baseline when exact not found)."""
    try:
        expirations = list(tq.options)
    except Exception:
        return None, None
    now = datetime.now()
    best = None
    best_dte = 0
    for e in expirations:
        try:
            d = datetime.strptime(e, "%Y-%m-%d")
            dte = (d.date() - now.date()).days
            if dte > best_dte:
                best = e
                best_dte = dte
        except ValueError:
            continue
    return best, best_dte if best_dte > 0 else None


def get_atm_iv(tq, current_price, exp_str):
    """Fetch ATM IV (calls only) for a given expiration."""
    try:
        chain = tq.option_chain(exp_str)
        calls = chain.calls.copy()
    except Exception:
        return np.nan

    if len(calls) == 0:
        return np.nan

    # Liquidity filter
    calls['volume'] = calls['volume'].fillna(0)
    calls['openInterest'] = calls['openInterest'].fillna(0)
    calls = calls[
        ((calls['volume'] > MIN_LIQUID_VOLUME) |
         (calls['openInterest'] > MIN_LIQUID_OI)) &
        (calls['impliedVolatility'].notna()) &
        (calls['impliedVolatility'] > 0.05) &
        (calls['impliedVolatility'] < 3.0)
    ].copy()

    if len(calls) < MIN_OPS:
        return np.nan

    # Robust ATM: median IV of strikes within ±2% moneyness
    moneyness = calls['strike'] / current_price
    atm_candidates = calls[(moneyness >= 0.98) & (moneyness <= 1.02)]
    if len(atm_candidates) >= 3:
        return float(atm_candidates['impliedVolatility'].median())

    # Fallback: closest strike with valid IV
    valid = calls[calls['impliedVolatility'] > 0.05]
    if len(valid) == 0:
        return np.nan
    idx = (valid['strike'] - current_price).abs().idxmin()
    return float(valid.loc[idx, 'impliedVolatility'])


def compute_signal(ticker_str):
    """Compute term structure slope for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        near_exp, near_dte = find_exp_by_dte(tq, NEAR_DTE, window=5)
        if near_exp is None:
            return None

        far_exp, far_dte = find_exp_by_dte(tq, FAR_DTE, window=10)
        # Fallback: use farthest available if exact target not found
        if far_exp is None:
            far_exp, far_dte = get_farthest_expiration(tq)

        if far_exp is None or near_dte >= far_dte:
            return None

        near_iv = get_atm_iv(tq, current_price, near_exp)
        far_iv = get_atm_iv(tq, current_price, far_exp)

        if np.isnan(near_iv) or np.isnan(far_iv) or near_iv <= 0:
            return None

        slope_norm = (far_iv - near_iv) / near_iv  # normalized slope (pct)

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'near_dte': int(near_dte),
            'far_dte': int(far_dte),
            'near_atm_iv': round(near_iv, 4),
            'far_atm_iv': round(far_iv, 4),
            'slope_norm_pct': round(slope_norm * 100, 2),  # percent
            'n_expirations': len(tq.options),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📈 IV Term Structure Slope (Refined) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Near tenor: {NEAR_DTE} DTE | Far tenor: {FAR_DTE} DTE (or farthest available)")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_signal(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   slope_norm_pct < 0 → backwardation (fear/stress, mean-reversion long)")
    print("   slope_norm_pct > 0 → contango (complacency)")

    os.makedirs("data", exist_ok=True)
    path = "data/iv_term_refined_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")