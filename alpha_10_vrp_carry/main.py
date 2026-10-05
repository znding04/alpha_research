#!/usr/bin/env python3
"""VRP Carry / Roll-down alpha signal.

Computes the carry/roll-down from Variance Risk Premium (VRP) term structure.
VRP Carry = VRP(short) - VRP(long)  [positive = earn carry by selling short-term, buying long-term]
Roll-down = VRP(t) - VRP(t+1) as options approach expiry (VRP typically decays toward expiry).
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_realized_vol(ticker_str, window=20):
    """Compute realized volatility from daily returns."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{window + 10}d")
        if len(hist) < window + 1:
            return np.nan
        returns = hist['Close'].pct_change().dropna()
        rv = returns.tail(window).std() * np.sqrt(252)
        return rv
    except Exception:
        return np.nan


def get_atm_iv(ticker_str, target_dte=None):
    """Get ATM IV for a given target DTE (or nearest liquid expiration)."""
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
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append((d, (d - now).days))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None, None

        # Select expiration
        if target_dte:
            # Find closest to target DTE
            exp_date, dte = min(valid_exps, key=lambda x: abs(x[1] - target_dte))
        else:
            # Use nearest liquid (skip DTE < 5)
            filtered = [(d, dte) for d, dte in valid_exps if dte >= 5]
            exp_date, dte = filtered[0] if filtered else valid_exps[0]

        exp_str = exp_date.strftime("%Y-%m-%d")
        chain = tq.option_chain(exp_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # Fix dtypes
        df['volume'] = df['volume'].fillna(0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).astype(int)

        # Filter liquid options
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()

        if len(df) < 10:
            return None, None

        atm_idx = (df['strike'] - current_price).abs().idxmin()
        atm_iv = df.loc[atm_idx, 'impliedVolatility']

        return atm_iv, dte

    except Exception:
        return None, None


def compute_vrp_carry(ticker_str):
    """Compute VRP carry metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        # Get realized vol (20-day)
        rv = get_realized_vol(ticker_str, window=20)
        if pd.isna(rv) or rv <= 0:
            return None

        # Get ATM IV for multiple expirations to build term structure
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append((d, (d - now).days))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if len(valid_exps) < 2:
            return None

        vrp_by_dte = []
        for exp_date, dte in valid_exps:
            if dte < 5:  # Skip very short DTE (noisy)
                continue
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                df = pd.concat([chain.calls, chain.puts], ignore_index=True)
                df['volume'] = df['volume'].fillna(0).astype(int)
                df['openInterest'] = df['openInterest'].fillna(0).astype(int)
                df = df[
                    ((df['volume'] > 10) | (df['openInterest'] > 100)) &
                    (df['impliedVolatility'].notna()) &
                    (df['impliedVolatility'] > 0.01) &
                    (df['impliedVolatility'] < 3.0) &
                    (df['lastPrice'] > 0)
                ].copy()
                if len(df) < 10:
                    continue
                atm_idx = (df['strike'] - current_price).abs().idxmin()
                atm_iv = df.loc[atm_idx, 'impliedVolatility']
                if pd.isna(atm_iv) or atm_iv <= 0:
                    continue
                vrp = atm_iv**2 - rv**2  # VRP = IV^2 - RV^2 (variance space)
                vrp_by_dte.append({'dte': dte, 'atm_iv': atm_iv, 'vrp': vrp})
            except Exception:
                continue

        if len(vrp_by_dte) < 2:
            return None

        vrp_df = pd.DataFrame(vrp_by_dte).sort_values('dte')

        # Near-term (shortest DTE >= 5) and far-term (longest DTE)
        near = vrp_df.iloc[0]
        far = vrp_df.iloc[-1]

        # VRP Carry = Near VRP - Far VRP (positive = steep term structure, earn carry by rolling)
        vrp_carry = near['vrp'] - far['vrp']

        # Roll-down estimate: daily VRP decay from term structure slope
        # Slope = (far_vrp - near_vrp) / (far_dte - near_dte) [VRP per day]
        dte_diff = far['dte'] - near['dte']
        if dte_diff > 0:
            vrp_slope = (far['vrp'] - near['vrp']) / dte_diff  # VRP change per day
            roll_down_daily = -vrp_slope  # Positive = VRP decays as DTE decreases
        else:
            vrp_slope = np.nan
            roll_down_daily = np.nan

        # VRP level (near-term)
        near_vrp = near['vrp']
        far_vrp = far['vrp']

        # Carry ratio: carry per unit of near-term VRP
        carry_ratio = vrp_carry / near_vrp if near_vrp != 0 else np.nan

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'realized_vol_20d': round(rv, 4),
            'near_dte': int(near['dte']),
            'far_dte': int(far['dte']),
            'near_atm_iv': round(near['atm_iv'], 4),
            'far_atm_iv': round(far['atm_iv'], 4),
            'near_vrp': round(near_vrp, 6),
            'far_vrp': round(far_vrp, 6),
            'vrp_carry': round(vrp_carry, 6),
            'vrp_slope_per_day': round(vrp_slope, 8),
            'roll_down_daily': round(roll_down_daily, 8),
            'carry_ratio': round(carry_ratio, 4),
            'n_expirations': len(vrp_df),
            'vrp_by_dte': vrp_df.to_dict('records'),
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 VRP Carry / Roll-down Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_vrp_carry(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  RV (20d):       {r['realized_vol_20d']:.4f}")
        print(f"  Near IV ({r['near_dte']}d):  {r['near_atm_iv']:.4f} | VRP: {r['near_vrp']:.6f}")
        print(f"  Far IV ({r['far_dte']}d):   {r['far_atm_iv']:.4f} | VRP: {r['far_vrp']:.6f}")
        print(f"  VRP Carry:      {r['vrp_carry']:.6f}")
        print(f"  Roll-down/day:  {r['roll_down_daily']:.8f}")
        print(f"  Carry Ratio:    {r['carry_ratio']:.4f}")
        print(f"  Expirations:    {r['n_expirations']}")

    # Save detailed data
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_carry_latest.csv"

    # Flatten for CSV
    flat_rows = []
    for r in results:
        for exp_data in r['vrp_by_dte']:
            flat_rows.append({
                'ticker': r['ticker'],
                'current_price': r['current_price'],
                'realized_vol_20d': r['realized_vol_20d'],
                'dte': exp_data['dte'],
                'atm_iv': exp_data['atm_iv'],
                'vrp': exp_data['vrp'],
            })

    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved detailed data to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")