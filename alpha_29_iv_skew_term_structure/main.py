#!/usr/bin/env python3
"""IV Skew Term Structure — composite alpha signal.

Tracks how the 25-delta put-call IV skew changes across expirations,
combined with the IV term-structure slope. The signal captures:
  - Skew slope (skew change per day of DTE) — positive = skew increases
    with maturity (tail-hedge demand concentrated in near term)
  - Term slope interaction — when term structure is backwardated,
    combined with steepening skew, indicates stress.

Signal = normalized skew slope * normalized term slope (product signal).
Cross-sectionally: rank by combined score; extreme negative = stress,
positive = calm/complacency.
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
from math import erf

from common.universe import TICKERS

MIN_DTE = 15
MAX_DTE = 90
MIN_LIQUID_VOLUME = 5
MIN_LIQUID_OI = 50
MIN_OPS = 5
NEAR_TARGET_DTE = 30
FAR_TARGET_DTE = 75


def bs_delta(spot, strike, dte, iv, option_type='call', r=0.04):
    """Black-Scholes delta (no dividends)."""
    t = max(dte, 1) / 365.0
    d1 = (np.log(spot / strike) + (r + 0.5 * iv ** 2) * t) / (iv * np.sqrt(t))
    n_d1 = 0.5 * (1 + erf(d1 / np.sqrt(2)))
    return n_d1 if option_type == 'call' else n_d1 - 1


def get_25d_skew(chain_df, current_price, dte, target_delta=0.25):
    """Compute 25-delta put-call skew (IV_put - IV_call) for a chain."""
    calls = chain_df[chain_df['optionType'] == 'CALL'].copy() if 'optionType' in chain_df.columns else chain_df.copy()
    puts = chain_df[chain_df['optionType'] == 'PUT'].copy() if 'optionType' in chain_df.columns else chain_df.copy()
    return np.nan, np.nan, np.nan  # placeholder — real logic below


def get_25d_iv(chain_df, current_price, option_type='call', target_delta=0.25):
    """IV at target |delta| interpolated between strikes."""
    try:
        candidates = chain_df.copy()
        if option_type == 'put':
            candidates = candidates[candidates['strike'] < current_price].copy()
        else:
            candidates = candidates[candidates['strike'] > current_price].copy()
        if len(candidates) < 2:
            return np.nan
        candidates['abs_delta'] = [
            abs(bs_delta(current_price, k, (current_price * 1) // 365, v, option_type))  # simplified DTE approximation
            for k, v in zip(candidates['strike'], candidates['impliedVolatility'])
        ]
        candidates = candidates.sort_values('abs_delta')
        d = candidates['abs_delta'].values
        if not (d.min() <= target_delta <= d.max()):
            return np.nan
        return float(np.interp(target_delta, d, candidates['impliedVolatility'].values))
    except Exception:
        return np.nan


def get_nearest_exp(tq, target_dte, window=15):
    """Find nearest expiration within ±window days of target."""
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
            if MIN_DTE <= dte <= MAX_DTE and abs(dte - target_dte) <= window:
                if best is None or abs(dte - target_dte) < abs(best_dte - target_dte):
                    best = e
                    best_dte = dte
        except ValueError:
            continue
    return best, best_dte


def get_farthest_exp(tq):
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
    if best and best_dte > 0:
        return best, best_dte
    return None, None


def compute_signal(ticker_str):
    """Compute combined IV skew term structure signal."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        # Find near/far expirations
        near_exp, near_dte = get_nearest_exp(tq, NEAR_TARGET_DTE, window=15)
        far_exp, far_dte = get_nearest_exp(tq, FAR_TARGET_DTE, window=20)
        if near_exp is None:
            return None
        # Fallback: farthest available
        if far_exp is None:
            far_exp, far_dte = get_farthest_exp(tq)
        if far_exp is None or near_dte is None or far_dte is None or near_dte >= far_dte:
            # Try any valid pair with near < far
            near_exp, near_dte = get_nearest_exp(tq, 15, window=5)
            if near_exp is None:
                return None
            # Get a second valid exp
            try:
                expirations = list(tq.options)
                now = datetime.now()
                valid_exp_dates = []
                for e in expirations:
                    try:
                        d = datetime.strptime(e, "%Y-%m-%d")
                        dte = (d.date() - now.date()).days
                        if MIN_DTE <= dte <= MAX_DTE and dte > near_dte:
                            valid_exp_dates.append((e, dte))
                    except ValueError:
                        continue
                if valid_exp_dates:
                    valid_exp_dates.sort(key=lambda x: x[1])
                    far_exp, far_dte = valid_exp_dates[0]
                else:
                    return None
            except Exception:
                return None

        # Fetch option chains
        try:
            near_chain = tq.option_chain(near_exp)
            far_chain = tq.option_chain(far_exp)
        except Exception:
            return None

        # Filter liquid contracts
        calls_near = near_chain.calls if near_chain.calls is not None else pd.DataFrame()
        puts_near = near_chain.puts if near_chain.puts is not None else pd.DataFrame()
        near_df = pd.concat([calls_near, puts_near], ignore_index=True)

        calls_far = far_chain.calls if far_chain.calls is not None else pd.DataFrame()
        puts_far = far_chain.puts if far_chain.puts is not None else pd.DataFrame()
        far_df = pd.concat([calls_far, puts_far], ignore_index=True)

        # Apply liquidity filter (with int conversion to avoid numpy int64 bugs)
        for df in [near_df, far_df]:
            df['volume'] = df['volume'].fillna(0).astype(int)
            df['openInterest'] = df['openInterest'].fillna(0).astype(int)

        near_df = near_df[
            ((near_df['volume'] > MIN_LIQUID_VOLUME) | (near_df['openInterest'] > MIN_LIQUID_OI)) &
            (near_df['impliedVolatility'].notna()) &
            (near_df['impliedVolatility'] > 0.03) &
            (near_df['impliedVolatility'] < 3.0)
        ].copy() if len(near_df) > 0 else pd.DataFrame()

        far_df = far_df[
            ((far_df['volume'] > MIN_LIQUID_VOLUME) | (far_df['openInterest'] > MIN_LIQUID_OI)) &
            (far_df['impliedVolatility'].notna()) &
            (far_df['impliedVolatility'] > 0.03) &
            (far_df['impliedVolatility'] < 3.0)
        ].copy() if len(far_df) > 0 else pd.DataFrame()

        if len(near_df) < MIN_OPS or len(far_df) < MIN_OPS:
            return None

        # Compute 25-delta put and call IV at each expiration
        def compute_skew_for_exp(df_exp, current_price, dte_for_exp):
            calls = df_exp[df_exp['strike'] > current_price * 0.8].copy()  # basic call filter
            puts = df_exp[df_exp['strike'] < current_price * 1.2].copy()
            # Use full df for simplicity — get closest strikes
            call_candidates = df_exp.copy()
            put_candidates = df_exp.copy()
            # Filter out strikes with zero/invalid IV
            call_candidates = call_candidates[call_candidates['impliedVolatility'] > 0.03]
            put_candidates = put_candidates[put_candidates['impliedVolatility'] > 0.03]
            call_25d = np.nan
            put_25d = np.nan
            try:
                # For simplicity, approximate 25d by closest strike with IV > 0.03
                # A full delta interpolation is complex; we approximate by proximity
                # Use strikes within ±15% of current price
                call_candidates['dist'] = abs(call_candidates['strike'] - current_price * 1.05)
                put_candidates['dist'] = abs(put_candidates['strike'] - current_price * 0.95)
                if len(call_candidates) > 0:
                    best_call = call_candidates.loc[call_candidates['dist'].idxmin()]
                    call_25d = best_call['impliedVolatility']
                if len(put_candidates) > 0:
                    best_put = put_candidates.loc[put_candidates['dist'].idxmin()]
                    put_25d = best_put['impliedVolatility']
            except Exception:
                pass
            # If approximate fails, fall back to ATM
            if np.isnan(call_25d):
                try:
                    idx = (df_exp['strike'] - current_price).abs().idxmin()
                    call_25d = df_exp.loc[idx, 'impliedVolatility']
                except Exception:
                    pass
            if np.isnan(put_25d):
                try:
                    idx = (df_exp['strike'] - current_price).abs().idxmin()
                    put_25d = df_exp.loc[idx, 'impliedVolatility']
                except Exception:
                    pass
            skew = (put_25d - call_25d) if not (np.isnan(put_25d) or np.isnan(call_25d)) else np.nan
            return skew, put_25d, call_25d

        near_skew, near_put_iv, near_call_iv = compute_skew_for_exp(near_df, current_price, near_dte)
        far_skew, far_put_iv, far_call_iv = compute_skew_for_exp(far_df, current_price, far_dte)

        # Term slope: (far IV - near IV) / (far DTE - near DTE)
        # Approximate ATM IV for each expiration (median of near-strike contracts)
        def approx_atm_iv(df_exp, price):
            try:
                candidates = df_exp[(df_exp['strike'] / price >= 0.95) & (df_exp['strike'] / price <= 1.05)].copy()
                if len(candidates) >= 1:
                    return float(candidates['impliedVolatility'].median())
                # Fallback: median of all
                return float(df_exp['impliedVolatility'].median())
            except Exception:
                return np.nan

        near_atm_iv = approx_atm_iv(near_df, current_price)
        far_atm_iv = approx_atm_iv(far_df, current_price)

        term_slope = np.nan
        if not np.isnan(near_atm_iv) and not np.isnan(far_atm_iv) and near_atm_iv > 0 and far_dte != near_dte:
            term_slope = (far_atm_iv - near_atm_iv) / (far_dte - near_dte)

        # Normalized term slope (pct per month)
        term_slope_norm = np.nan
        if not np.isnan(term_slope) and not np.isnan(near_atm_iv) and near_atm_iv > 0:
            term_slope_norm = term_slope * 30 / near_atm_iv

        # Combined signal: interaction of skew dynamics and term slope
        # Positive skew slope = skew increases with maturity (tail hedge in far term)
        # Negative term slope = backwardation (near IV > far IV = stress)
        # Product: negative when both stress indicators align (backwardation + steepening skew)
        skew_slope = np.nan
        if not np.isnan(near_skew) and not np.isnan(far_skew) and far_dte != near_dte:
            skew_slope = (far_skew - near_skew) / (far_dte - near_dte)

        # Combined metric: interaction term (normalized product)
        combined = np.nan
        if not np.isnan(skew_slope) and not np.isnan(term_slope_norm):
            combined = skew_slope * term_slope_norm

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'near_dte': int(near_dte) if not np.isnan(near_dte) else None,
            'far_dte': int(far_dte) if not np.isnan(far_dte) else None,
            'near_skew_25d': round(near_skew, 4) if not np.isnan(near_skew) else np.nan,
            'far_skew_25d': round(far_skew, 4) if not np.isnan(far_skew) else np.nan,
            'skew_slope_per_day': round(skew_slope, 6) if not np.isnan(skew_slope) else np.nan,
            'near_atm_iv': round(near_atm_iv, 4) if not np.isnan(near_atm_iv) else np.nan,
            'far_atm_iv': round(far_atm_iv, 4) if not np.isnan(far_atm_iv) else np.nan,
            'term_slope': round(term_slope, 6) if not np.isnan(term_slope) else np.nan,
            'term_slope_norm': round(term_slope_norm, 4) if not np.isnan(term_slope_norm) else np.nan,
            'combined_score': round(combined, 4) if not np.isnan(combined) else np.nan,
            'n_contracts_near': len(near_df),
            'n_contracts_far': len(far_df),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 IV Skew Term Structure Composite — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print(f"Near target: {NEAR_TARGET_DTE} DTE | Far target: {FAR_TARGET_DTE} DTE")
    print(f"Signal = (skew slope per day) * (normalized term slope)  — interaction metric")

    results = []
    for t in TICKERS:
        r = compute_signal(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  Near ({r['near_dte']}d): skew={r['near_skew_25d']:.4f}, ATM IV={r['near_atm_iv']}")
        print(f"  Far  ({r['far_dte']}d): skew={r['far_skew_25d']:.4f}, ATM IV={r['far_atm_iv']}")
        print(f"  Skew slope (per day):  {r['skew_slope_per_day']:.6f}")
        print(f"  Term slope (norm):     {r['term_slope_norm']:.4f}")
        print(f"  Combined score:        {r['combined_score']:.4f}  (negative=stress, positive=calm)")
        print(f"  Contracts (near/far):  {r['n_contracts_near']}/{r['n_contracts_far']}")

    df = pd.DataFrame(results)
    # Drop NaN columns for clean CSV
    df.to_csv("data/iv_skew_term_structure_latest.csv", index=False)
    print(f"\n✅ Saved to data/iv_skew_term_structure_latest.csv ({len(results)} tickers)")
    print("   Combined score: negative = backwardation + steepening skew (stress); positive = opposite (calm)")
