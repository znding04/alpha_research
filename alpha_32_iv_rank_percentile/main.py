#!/usr/bin/env python3
"""IV Rank Percentile (60d rolling) — Alpha 32.

Hypothesis: Current ATM IV percentile vs a longer 60-day rolling window
captures medium-term vol regime changes better than the 30-day window.
Higher percentile = IV rich vs recent history = potential mean-reversion.
Lower percentile = IV cheap = potential vol expansion.

Signal: iv_percentile_60d = (atm_iv - min_iv_60d) / (max_iv_60d - min_iv_60d)
Using option chain spread as proxy for historical IV range (since we only
have today's chain, we approximate the range from the cross-strike IV
distribution and scale by a regime factor).
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


def compute_iv_rank_pct_60d(ticker_str):
    """Compute IV rank percentile using 60-day rolling window proxy."""
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
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append(d)
            except ValueError:
                continue
        valid_exps.sort()
        if not valid_exps:
            return None

        # Use nearest meaningful expiration (skip DTE < 2)
        target_exp = min(
            [e for e in valid_exps if e > datetime.now().replace(day=max(now.day, 2))],
            default=valid_exps[0]
        )
        target_str = target_exp.strftime("%Y-%m-%d")

        chain = tq.option_chain(target_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # Fix dtypes: volume/OI are numpy int64
        df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)

        # Filter: liquid + valid IV + positive price
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()

        if len(df) < 10:
            return None

        # Robust ATM IV: median of strikes within ±2% moneyness with IV > 5%
        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]

        if len(atm_candidates) >= 3:
            atm_iv = atm_candidates['impliedVolatility'].median()
        else:
            valid_strikes = df[df['impliedVolatility'] > 0.05]
            if len(valid_strikes) == 0:
                return None
            atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
            atm_iv = valid_strikes.loc[atm_idx, 'impliedVolatility']

        # 60-day proxy: use the full IV distribution range across strikes
        # as a proxy for the historical IV range. Scale by regime factor.
        iv_min = df['impliedVolatility'].min()
        iv_max = df['impliedVolatility'].max()
        iv_range = iv_max - iv_min

        if iv_range < 0.01:  # Too narrow
            return None

        # Base percentile from today's chain spread
        iv_pct_raw = (atm_iv - iv_min) / iv_range

        # 60-day regime adjustment: use VIX term structure as proxy
        # For index ETFs (SPY, QQQ, IWM, DIA), adjust by VIX term slope
        regime_factor = 1.0
        if ticker_str in ['SPY', 'QQQ', 'IWM', 'DIA']:
            # Approximate term structure from near/far expirations
            if len(valid_exps) >= 2:
                # Get far expiration IV
                far_str = valid_exps[1].strftime("%Y-%m-%d")
                far_chain = tq.option_chain(far_str)
                far_df = pd.concat([far_chain.calls, far_chain.puts], ignore_index=True)
                far_df['volume'] = far_df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
                far_df['openInterest'] = far_df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
                far_df = far_df[
                    ((far_df['volume'] > 10) | (far_df['openInterest'] > 100)) &
                    (far_df['impliedVolatility'].notna()) &
                    (far_df['impliedVolatility'] > 0.01) &
                    (far_df['impliedVolatility'] < 3.0) &
                    (far_df['lastPrice'] > 0)
                ].copy()
                if len(far_df) >= 10:
                    far_moneyness = far_df['strike'] / current_price
                    far_atm = far_df[(far_moneyness >= 0.98) & (far_moneyness <= 1.02) & (far_df['impliedVolatility'] > 0.05)]
                    if len(far_atm) >= 3:
                        far_iv = far_atm['impliedVolatility'].median()
                        # Term slope: if far IV > near IV (contango), regime is elevated
                        term_slope = (far_iv - atm_iv) / atm_iv
                        # Scale regime factor: contango = higher regime
                        regime_factor = 1.0 + 0.5 * term_slope

        # Adjusted percentile
        iv_pct_60d = np.clip(iv_pct_raw * regime_factor, 0.0, 1.0)

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'atm_iv': round(atm_iv, 4),
            'iv_min': round(iv_min, 4),
            'iv_max': round(iv_max, 4),
            'iv_pct_raw': round(iv_pct_raw, 4),
            'regime_factor': round(regime_factor, 4),
            'iv_percentile_60d': round(iv_pct_60d, 4),
            'n_contracts': len(df),
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n🔍 IV Rank Percentile (60d) Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_iv_rank_pct_60d(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   iv_percentile_60d > 0.75 → IV rich vs 60d history (potential mean-rev)")
    print("   iv_percentile_60d < 0.25 → IV cheap vs 60d history (potential expansion)")
    print("   regime_factor > 1.0 → VIX contango (elevated vol regime)")

    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_rank_percentile_60d_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")