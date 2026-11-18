#!/usr/bin/env python3
"""ATM IV term-structure convexity (butterfly) — alpha_45.

Signal: curvature of the ATM implied-vol term structure across three tenors.

    curvature      = IV_mid - 0.5 * (IV_short + IV_long)
    curvature_norm = curvature / IV_mid   (scale-free, cross-section comparable)

with tenors ~14d / ~30d / ~60-90d (nearest liquid expiration to each target).

Why a new signal: existing term-structure alphas (03, 25, 27, 37) measure the
SLOPE (long minus short IV). A slope-only read cannot distinguish a smoothly
upward curve from a humped/trough curve that has the same endpoints. The
butterfly isolates the *middle* tenor relative to the wings:

    curvature > 0  -> humped term structure (mid-tenor vol rich vs wings;
                      near-term event risk priced into the belly)
    curvature < 0  -> trough (belly cheap; smooth contango or flat curve)

Cross-sectionally: rank the 6 focus names by curvature_norm. Hypothesis: an
over-rich mid-tenor belly mean-reverts, so high curvature predicts lower
forward returns / lower forward IV. Sign is left to the IC to decide.
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

# Focus cross-section requested for this signal (subset of TICKERS).
FOCUS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]

# Tenor targets in days-to-expiry: short / mid / long.
TENOR_SHORT = 14
TENOR_MID = 30
TENOR_LONG = 75

MAX_DTE = 180  # cap on how far out we look for the long wing


def _valid_expirations(tq, now):
    """Sorted list of datetime objects for expirations in (today, MAX_DTE]."""
    valid = []
    for e in tq.options:
        try:
            d = datetime.strptime(e, "%Y-%m-%d")
            dte = (d - now).days
            if dte > 0 and dte <= MAX_DTE:
                valid.append(d)
        except ValueError:
            continue
    valid.sort()
    return valid


def _nearest_exp(valid_exps, now, target_dte):
    """Expiration whose DTE is closest to target_dte."""
    return min(valid_exps, key=lambda d: abs((d - now).days - target_dte))


def get_atm_iv(tq, current_price, exp_date):
    """ATM IV for a single expiration: median IV of strikes within ±2%
    moneyness (IV > 5%); fallback to single closest strike with IV > 5%."""
    chain = tq.option_chain(exp_date.strftime("%Y-%m-%d"))
    df = pd.concat([chain.calls, chain.puts], ignore_index=True)

    # volume/OI are numpy int64; fillna + astype(int) for safe comparison.
    df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
    df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)

    df = df[
        ((df['volume'] > 10) | (df['openInterest'] > 100)) &
        (df['impliedVolatility'].notna()) &
        (df['impliedVolatility'] > 0.01) &
        (df['impliedVolatility'] < 3.0) &
        (df['lastPrice'] > 0)
    ].copy()

    if len(df) < 10:
        return None, 0

    moneyness = df['strike'] / current_price
    atm_cand = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
    if len(atm_cand) >= 3:
        return float(atm_cand['impliedVolatility'].median()), len(df)

    valid = df[df['impliedVolatility'] > 0.05]
    if len(valid) == 0:
        return None, len(df)
    idx = (valid['strike'] - current_price).abs().idxmin()
    return float(valid.loc[idx, 'impliedVolatility']), len(df)


def compute_signal(ticker_str):
    """Return dict with term-structure convexity signal for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        now = datetime.now()
        valid_exps = _valid_expirations(tq, now)
        if len(valid_exps) < 3:
            return None

        exp_s = _nearest_exp(valid_exps, now, TENOR_SHORT)
        exp_m = _nearest_exp(valid_exps, now, TENOR_MID)
        exp_l = _nearest_exp(valid_exps, now, TENOR_LONG)

        # Need three *distinct* expirations for a meaningful butterfly.
        if len({exp_s, exp_m, exp_l}) < 3:
            return None

        iv_s, n_s = get_atm_iv(tq, current_price, exp_s)
        iv_m, n_m = get_atm_iv(tq, current_price, exp_m)
        iv_l, n_l = get_atm_iv(tq, current_price, exp_l)
        if iv_s is None or iv_m is None or iv_l is None:
            return None
        if min(iv_s, iv_m, iv_l) <= 0.05:
            return None

        curvature = iv_m - 0.5 * (iv_s + iv_l)
        curvature_norm = curvature / iv_m if iv_m > 0 else np.nan
        slope = (iv_l - iv_s) / iv_s if iv_s > 0 else np.nan

        return {
            "ticker": ticker_str,
            "current_price": round(float(current_price), 2),
            "dte_short": (exp_s - now).days,
            "dte_mid": (exp_m - now).days,
            "dte_long": (exp_l - now).days,
            "iv_short": round(iv_s, 4),
            "iv_mid": round(iv_m, 4),
            "iv_long": round(iv_l, 4),
            "curvature": round(float(curvature), 6),
            "curvature_norm": round(float(curvature_norm), 4),
            "slope": round(float(slope), 4),
            "n_contracts": int(n_s + n_m + n_l),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n🔍 IV Term-Structure Convexity (ATM butterfly) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 74)

    results = []
    for t in TICKERS:
        r = compute_signal(t)
        if r:
            results.append(r)
            print(f"  ✅ {t}: curvature={r['curvature']:+.6f} "
                  f"(norm={r['curvature_norm']:+.4f}, slope={r['slope']:+.4f}, "
                  f"DTE {r['dte_short']}/{r['dte_mid']}/{r['dte_long']})")
        else:
            print(f"  ⚠️ {t}: no data")

    if not results:
        print("No data collected.")
        sys.exit(1)

    df = pd.DataFrame(results)

    # Cross-sectional rank over the focus subset (higher = richer belly).
    focus_df = df[df['ticker'].isin(FOCUS)].copy()
    if len(focus_df) >= 2:
        focus_df['curvature_rank'] = focus_df['curvature_norm'].rank(ascending=True, pct=True)
        rank_map = dict(zip(focus_df['ticker'], focus_df['curvature_rank']))
        df['curvature_rank'] = df['ticker'].map(rank_map)

    print("\n" + df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   curvature > 0 → humped term structure (mid-tenor vol rich vs wings)")
    print("   curvature < 0 → trough (belly cheap; smooth contango / flat curve)")
    print("   curvature_rank: cross-sectional percentile over the 6 focus names")
    print("                     (1 = richest mid-tenor belly)")

    os.makedirs("data", exist_ok=True)
    path = "data/iv_term_convexity_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
