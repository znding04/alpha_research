#!/usr/bin/env python3
"""IV Calendar Spread alpha signal.

Computes the ATM IV spread between two nearby expirations (calendar spread).
Signal = IV(short_dte) - IV(long_dte) at ATM.

Cross-sectionally:
- Positive spread (short > long) = backwardation → elevated near-term fear/hedging demand
- Negative spread (short < long) = contango → complacency or roll-down opportunity
- Calendar spread mean-reversion: extreme spreads predict IV convergence

Key insight: Calendar spreads are delta-neutral and isolate term structure dynamics
without directional risk. They capture pure volatility term structure premium.
"""

import os
import sys
sys.path.insert(0, "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_atm_iv(ticker_str, target_dte, max_dte=180):
    """Get ATM IV for a specific target DTE by finding closest available expiration."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None, None

        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 0 < dte <= max_dte:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None, None

        # Find expiration closest to target DTE
        exp_date, dte = min(valid_exps, key=lambda x: abs(x[1] - target_dte))
        exp_str = exp_date.strftime("%Y-%m-%d")

        chain = tq.option_chain(exp_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # Fix dtypes - avoid astype(int) on NaN/inf
        df['volume'] = df['volume'].fillna(0)
        df['openInterest'] = df['openInterest'].fillna(0)

        # Filter liquid options with valid IV
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()

        if len(df) < 10:
            return None, None

        # Find ATM strike (closest to spot)
        atm_idx = (df['strike'] - current_price).abs().idxmin()
        atm_iv = df.loc[atm_idx, 'impliedVolatility']
        atm_strike = df.loc[atm_idx, 'strike']

        if pd.isna(atm_iv) or atm_iv <= 0:
            return None, None

        return atm_iv, dte

    except Exception:
        return None, None


def compute_calendar_spread(ticker_str, short_dte=30, long_dte=60):
    """Compute IV calendar spread metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        # Get ATM IV for both expirations
        short_iv, short_actual_dte = get_atm_iv(ticker_str, short_dte)
        long_iv, long_actual_dte = get_atm_iv(ticker_str, long_dte)

        if short_iv is None or long_iv is None:
            return None

        # Calendar spread: short IV - long IV (in vol points)
        cal_spread_vol = short_iv - long_iv

        # Calendar spread in variance space (more economically meaningful)
        short_var = short_iv ** 2
        long_var = long_iv ** 2
        cal_spread_var = short_var - long_var

        # Normalized spread (as % of long-term IV)
        cal_spread_pct = cal_spread_vol / long_iv if long_iv > 0 else np.nan

        # Slope per day
        dte_diff = long_actual_dte - short_actual_dte
        if dte_diff > 0:
            slope_per_day = cal_spread_vol / dte_diff
        else:
            slope_per_day = np.nan

        # Term structure regime classification
        if cal_spread_vol > 0.02:  # >2 vol points backwardation
            regime = "BACKWARDATION"
        elif cal_spread_vol < -0.02:  # >2 vol points contango
            regime = "CONTANGO"
        else:
            regime = "FLAT"

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'short_dte_target': short_dte,
            'long_dte_target': long_dte,
            'short_actual_dte': int(short_actual_dte),
            'long_actual_dte': int(long_actual_dte),
            'short_atm_iv': round(short_iv, 4),
            'long_atm_iv': round(long_iv, 4),
            'cal_spread_vol': round(cal_spread_vol, 4),
            'cal_spread_var': round(cal_spread_var, 6),
            'cal_spread_pct': round(cal_spread_pct, 4),
            'slope_per_day': round(slope_per_day, 6),
            'regime': regime,
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📅 IV Calendar Spread Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_calendar_spread(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  Short IV ({r['short_actual_dte']}d target {r['short_dte_target']}d): {r['short_atm_iv']:.4f}")
        print(f"  Long IV  ({r['long_actual_dte']}d target {r['long_dte_target']}d):  {r['long_atm_iv']:.4f}")
        print(f"  Calendar Spread (vol):  {r['cal_spread_vol']:.4f}")
        print(f"  Calendar Spread (var):  {r['cal_spread_var']:.6f}")
        print(f"  Spread % of Long IV:    {r['cal_spread_pct']:.4f}")
        print(f"  Slope per day:          {r['slope_per_day']:.6f}")
        print(f"  Regime:                 {r['regime']}")

    # Save to CSV
    os.makedirs("data", exist_ok=True)
    path = "data/iv_calendar_spread_latest.csv"
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")