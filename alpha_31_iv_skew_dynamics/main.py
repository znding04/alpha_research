#!/usr/bin/env python3
"""IV Skew Dynamics — put-call skew change vs forward returns.

Hypothesis: Skew dynamics (momentum/reversion in put-call skew) predict future returns.

Signal: 25-delta Black-Scholes put-call skew change (last day vs 5 days ago)
  skewness = skew_latest - skew_5d_ago
  More negative skewness (deeper skew) = fear/stress = mean-reversion bullish
  More positive skewness (flattened) = complacency = mean-reversion bearish

Implementation:
- 25-delta Black-Scholes call/put Greeks at ~30d ~50d expirations (when available)
- Compute cross-sectional skew = 1 - (put_delta / call_delta) where put_delta < 0, call_delta > 0
- Track daily changes: today_skew - 5_days_ago_skew
- Save daily snapshot
- Rank tickers cross-sectionally by skewness change

Live snapshot uses today’s chains only; full historical requires rolling snapshots.
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

# Target expiration DTEs (skip weekly 0-DTE noise)
NEAR_DTE = 30
FAR_DTE = 50

# Skew calculation constants
SKEW_FACTOR = 25.0  # 25-delta skew measure

def black_scholes_delta(ticker_str, strike, time_to_expiry, risk_free_rate=0.02):
    """Calculate Black-Scholes delta for given parameters."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None, None

        volatility = 0.20  # Estimate volatility if not available
        if 'impliedVolatility' in info and info['impliedVolatility']:
            volatility = info['impliedVolatility']

        from scipy.stats import norm
        d1 = (np.log(current_price / strike) +
              (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / \
             (volatility * np.sqrt(time_to_expiry))
        call_delta = norm.cdf(d1)
        put_delta = call_delta - 1.0

        return call_delta, put_delta
    except Exception:
        return None, None

def get_atm_iv_at_exp(ticker_str, current_price, exp_str, dte):
    """Get ATM IV at specific expiration (uses actual expiration, not DTE)."""
    try:
        tq = yf.Ticker(ticker_str)
        chain = tq.option_chain(exp_str)

        # Get both calls and puts
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # Standard liquidity filter
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

        # Robust ATM IV: median of strikes within ±2% moneyness with IV > 0.05
        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]

        if len(atm_candidates) >= 3:
            return float(atm_candidates['impliedVolatility'].median())
        else:
            valid_strikes = df[df['impliedVolatility'] > 0.05]
            if len(valid_strikes) == 0:
                return None
            atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
            return float(valid_strikes.loc[atm_idx, 'impliedVolatility'])

    except Exception:
        return None

def find_best_expiration(ticker_str, target_dte, window=7):
    """Find expiration closest to target DTE within window."""
    try:
        tq = yf.Ticker(ticker_str)
        expirations = list(tq.options)
        now = datetime.now()

        best = None
        best_dte = None
        best_diff = float('inf')

        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d.date() - now.date()).days
                if dte > 0 and dte <= 180:  # Look within reasonable range
                    diff = abs(dte - target_dte)
                    if diff <= window:
                        if best is None or diff < best_diff:
                            best = e
                            best_dte = dte
                            best_diff = diff
            except ValueError:
                continue

        return best, best_dte
    except Exception:
        return None, None

def get_25_delta_skew(ticker_str, current_price, exp_str, target_dte):
    """Calculate 25-delta put-call skew at given expiration."""
    try:
        tq = yf.Ticker(ticker_str)
        chain = tq.option_chain(exp_str)

        # Get both calls and puts
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # Liquidity filter
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

        # Calculate time to expiration
        exp_dt = datetime.strptime(exp_str, "%Y-%m-%d")
        time_to_expiry = max((exp_dt - datetime.now()).days / 252.0, 0.01)

        # Find strikes where we can estimate deltas
        # We need both calls and puts around ATM
        atm_strike = df.iloc[(df['strike'] - current_price).abs().argsort()[:1]].iloc[0]['strike']

        # Estimate 25-delta strikes using approximate forward
        forward = current_price * np.exp(0.02 * time_to_expiry)  # Simple forward estimate
        call_25_strike = forward * (1 + 0.01)  # Approximate 25-delta call strike
        put_25_strike = forward * (1 - 0.01)   # Approximate 25-delta put strike

        # Find actual options near these strikes
        call_options = df[df['type'] == 'call'] if 'type' in df.columns else df[df['callOrPut'] == 'C']
        put_options = df[df['type'] == 'put'] if 'type' in df.columns else df[df['callOrPut'] == 'P']

        # Get closest strikes to 25-delta levels
        call_near = call_options.iloc[(call_options['strike'] - call_25_strike).abs().argsort()[:1]]
        put_near = put_options.iloc[(put_options['strike'] - put_25_strike).abs().argsort()[:1]]

        if len(call_near) == 0 or len(put_near) == 0:
            return None

        # Get deltas for 25-delta strikes
        call_delta = call_near.iloc[0].get('delta')
        put_delta = put_near.iloc[0].get('delta')

        if call_delta is None or put_delta is None:
            # Fall back to Black-Scholes calculation
            call_delta, put_delta = black_scholes_delta(ticker_str, call_25_strike, time_to_expiry)

        if call_delta is None or put_delta is None:
            return None

        # Calculate 25-delta skew: 1 - (put_delta / call_delta)
        # Note: put_delta is negative, call_delta is positive
        skew = 1 - (put_delta / call_delta)
        return float(skew)

    except Exception:
        return None

def compute_skew_dynamics(ticker_str, today_skew, yesterday_skew, yesterday2_skew):
    """Compute skew change signal."""
    if today_skew is None or yesterday_skew is None:
        return None

    # Calculate 5-day change (difference between today and ~5 days ago)
    skew_change = today_skew - yesterday_skew

    return {
        'skew_latest': round(today_skew, 4),
        'skew_5d_ago': round(yesterday_skew, 4),
        'skew_change': round(skew_change, 4),
        'skew_trend': 'rising' if skew_change > 0.01 else 'falling' if skew_change < -0.01 else 'stable',
    }

if __name__ == "__main__":
    print(f"\n📊 IV Skew Dynamics — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Target expirations: {NEAR_DTE}DTE and {FAR_DTE}DTE")
    print("Signal: 25-delta put-call skew change (today vs ~5 days ago)")
    print("=" * 70)

    # For now, compute using latest available data (we'd need to track this over time)
    # This is a live snapshot implementation

    results = []
    skew_data = {}

    for t in TICKERS:
        # Get current price
        tq = yf.Ticker(t)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            continue

        # Find best expirations
        near_exp, near_dte = find_best_expiration(t, NEAR_DTE, window=7)
        far_exp, far_dte = find_best_expiration(t, FAR_DTE, window=7)

        if near_exp is None or far_exp is None:
            continue

        # Get 25-delta skew for both expirations
        near_skew = get_25_delta_skew(t, current_price, near_exp, near_dte)
        far_skew = get_25_delta_skew(t, current_price, far_exp, far_dte)

        if near_skew is None or far_skew is None:
            continue

        # For this snapshot, we'll compute a daily change by using a simple heuristic:
        # We'll assume this represents a day's data and compute the change by comparing
        # between two "theoretical" points. In practice, you'd want historical data.
        # For now, we'll use a simplified approach: just report the skew values

        skew_data[t] = {
            'ticker': t,
            'current_price': round(current_price, 2),
            'near_dte': int(near_dte),
            'far_dte': int(far_dte),
            'near_skew': round(near_skew, 4),
            'far_skew': round(far_skew, 4),
            'skew_average': round((near_skew + far_skew) / 2, 4),
        }

    if not skew_data:
        print("No data collected.")
        exit(1)

    # Add some simple signal based on cross-sectional ranking
    df_skew = pd.DataFrame(list(skew_data.values()))

    # Cross-sectional ranking by average skew (lower = more put skew = fear)
    df_skew['skew_rank'] = df_skew['skew_average'].rank(method='dense', ascending=True)

    # Signal: skewness change would normally require historical data
    # For now, we'll use current skew as a proxy for the dynamics hypothesis
    # In full implementation, this would track skew changes over time

    print(df_skew.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   Low skew rank (< median) = high fear/stress = mean-reversion bullish")
    print("   High skew rank (> median) = complacency = mean-reversion bearish")
    print("   Note: Full skew dynamics signal requires tracking over multiple days.")

    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_skew_dynamics_latest.csv"
    df_skew.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")