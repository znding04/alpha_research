#!/usr/bin/env python3
"""VRP Term Structure alpha signal.

Computes Variance Risk Premium (IV^2 - RV^2) across multiple expirations.
Signal = VRP term structure slope and curvature — captures how VRP varies with maturity.

Cross-sectionally:
- Steep VRP term structure (high near-term VRP) → elevated fear/hedging demand
- Flat/inverted VRP term structure → complacency or mean-reversion opportunity
- VRP slope change predicts forward equity returns
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


def compute_atm_iv_for_expiration(ticker_str, exp_date, current_price):
    """Get ATM IV for a specific expiration."""
    try:
        tq = yf.Ticker(ticker_str)
        exp_str = exp_date.strftime("%Y-%m-%d")
        chain = tq.option_chain(exp_str)
        calls = chain.calls
        puts = chain.puts

        # Filter liquid options
        calls = calls[
            (calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)
        ].copy()
        puts = puts[
            (puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)
        ].copy()

        if len(calls) < 5 or len(puts) < 5:
            return None

        # Find strikes within 5% of spot (near ATM)
        moneyness_low = current_price * 0.95
        moneyness_high = current_price * 1.05
        all_options = pd.concat([calls, puts], ignore_index=True)
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low) &
            (all_options['strike'] <= moneyness_high)
        ].copy()

        if len(near_atm) == 0:
            return None

        # Filter for liquid options with valid IV > 1%
        near_atm = near_atm[
            (near_atm['volume'].fillna(0) > 10) | (near_atm['openInterest'].fillna(0) > 100)
        ].copy()
        near_atm = near_atm[
            (near_atm['impliedVolatility'].notna()) &
            (near_atm['impliedVolatility'] > 0.01)
        ].copy()

        if len(near_atm) == 0:
            return None

        # Weighted average IV by liquidity
        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = (near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq
        else:
            atm_iv = near_atm['impliedVolatility'].median()

        return atm_iv if pd.notna(atm_iv) and atm_iv > 0 else None

    except Exception:
        return None


def compute_realized_vol(ticker_str, lookback_days=30):
    """Compute realized volatility from historical returns."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{lookback_days + 15}d")
        if len(hist) < lookback_days + 5:
            return np.nan

        close = hist['Close']
        log_returns = np.log(close / close.shift(1)).dropna()

        if len(log_returns) < lookback_days:
            return np.nan

        recent_returns = log_returns.iloc[-lookback_days:]
        rv = recent_returns.std() * np.sqrt(252)
        return rv if pd.notna(rv) and rv > 0 else np.nan

    except Exception:
        return np.nan


def get_valid_expirations(ticker_str, max_dte=180):
    """Get valid expirations within max_dte days."""
    try:
        tq = yf.Ticker(ticker_str)
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
        return valid_exps
    except Exception:
        return []


def compute_vrp_term_structure(ticker_str, rv_lookback=30, max_dte=180):
    """Compute VRP term structure metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            return None

        # Get realized volatility (same for all expirations)
        rv = compute_realized_vol(ticker_str, rv_lookback)
        if pd.isna(rv) or rv <= 0:
            return None
        rv_var = rv ** 2

        # Get valid expirations
        valid_exps = get_valid_expirations(ticker_str, max_dte)
        if len(valid_exps) < 2:
            return None

        results = []
        for exp_date, dte in valid_exps:
            atm_iv = compute_atm_iv_for_expiration(ticker_str, exp_date, current_price)
            if atm_iv is None:
                continue

            iv_var = atm_iv ** 2
            vrp_var = iv_var - rv_var
            vrp_vol = np.sqrt(max(vrp_var, 0)) if vrp_var > 0 else -np.sqrt(abs(vrp_var))
            vrp_ratio = iv_var / rv_var if rv_var > 0 else np.nan

            results.append({
                'expiration': exp_date.strftime("%Y-%m-%d"),
                'dte': dte,
                'atm_iv': atm_iv,
                'iv_variance': iv_var,
                'rv_variance': rv_var,
                'vrp_variance': vrp_var,
                'vrp_vol_points': vrp_vol,
                'vrp_ratio': vrp_ratio,
            })

        if len(results) < 2:
            return None

        df = pd.DataFrame(results)
        df = df.sort_values('dte')

        # VRP Term Structure Slope: (VRP_far - VRP_near) / (DTE_far - DTE_near)
        near_vrp = df.iloc[0]['vrp_variance']
        far_vrp = df.iloc[-1]['vrp_variance']
        near_dte = df.iloc[0]['dte']
        far_dte = df.iloc[-1]['dte']
        vrp_slope = (far_vrp - near_vrp) / (far_dte - near_dte) if far_dte != near_dte else np.nan

        # VRP Term Structure Curvature (3-point second derivative)
        vrp_curvature = np.nan
        if len(df) >= 3:
            mid_idx = len(df) // 2
            mid_vrp = df.iloc[mid_idx]['vrp_variance']
            mid_dte = df.iloc[mid_idx]['dte']
            vrp_curvature = (far_vrp - 2*mid_vrp + near_vrp) / ((far_dte - mid_dte) * (mid_dte - near_dte))

        # Average VRP across term structure
        avg_vrp_var = df['vrp_variance'].mean()
        avg_vrp_vol = df['vrp_vol_points'].mean()
        avg_vrp_ratio = df['vrp_ratio'].mean()

        # Near-term vs far-term VRP spread
        vrp_spread = far_vrp - near_vrp

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'realized_vol': round(rv, 4),
            'near_dte': int(near_dte),
            'far_dte': int(far_dte),
            'near_vrp_var': round(near_vrp, 6),
            'far_vrp_var': round(far_vrp, 6),
            'avg_vrp_var': round(avg_vrp_var, 6),
            'avg_vrp_vol': round(avg_vrp_vol, 4),
            'avg_vrp_ratio': round(avg_vrp_ratio, 4),
            'vrp_slope': round(vrp_slope, 8),
            'vrp_curvature': round(vrp_curvature, 10) if not pd.isna(vrp_curvature) else np.nan,
            'vrp_spread': round(vrp_spread, 6),
            'n_expirations': len(df),
            'term_structure': df.to_dict('records'),
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 VRP Term Structure Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_vrp_term_structure(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        slope = r['vrp_slope']
        spread = r['vrp_spread']
        slope_str = f"{slope:.8f}" if not pd.isna(slope) else "N/A"
        curve_str = f"{r['vrp_curvature']:.10f}" if not pd.isna(r['vrp_curvature']) else "N/A"

        # Interpretation
        if pd.isna(slope):
            signal = "⏳ Insufficient data"
        elif slope < -1e-6:
            signal = "📉 INVERTED VRP TERM — Near-term VRP premium (fear/stress)"
        elif slope > 1e-6:
            signal = "📈 NORMAL VRP TERM — Far-term VRP premium (contango)"
        else:
            signal = "➖ FLAT VRP TERM — Minimal term structure"

        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  Realized Vol (ann.): {r['realized_vol']:.4f}")
        print(f"  Near VRP ({r['near_dte']}d):    {r['near_vrp_var']:.6f}")
        print(f"  Far VRP  ({r['far_dte']}d):    {r['far_vrp_var']:.6f}")
        print(f"  Avg VRP (var):       {r['avg_vrp_var']:.6f}")
        print(f"  VRP Slope (per day): {slope_str}")
        print(f"  VRP Curvature:       {curve_str}")
        print(f"  VRP Spread (far-near): {spread:.6f}")
        print(f"  Expirations:         {r['n_expirations']}")
        print(f"  Signal:              {signal}")

    # Save detailed data
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_term_structure_latest.csv"

    flat_rows = []
    for r in results:
        for exp_data in r['term_structure']:
            flat_rows.append({
                'ticker': r['ticker'],
                'current_price': r['current_price'],
                'realized_vol': r['realized_vol'],
                'expiration': exp_data['expiration'],
                'dte': exp_data['dte'],
                'atm_iv': exp_data['atm_iv'],
                'iv_variance': exp_data['iv_variance'],
                'rv_variance': exp_data['rv_variance'],
                'vrp_variance': exp_data['vrp_variance'],
                'vrp_vol_points': exp_data['vrp_vol_points'],
                'vrp_ratio': exp_data['vrp_ratio'],
            })

    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved detailed data to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")