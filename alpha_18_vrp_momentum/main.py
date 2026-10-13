#!/usr/bin/env python3
"""VRP Momentum alpha signal.

Tracks rate of change of Variance Risk Premium (IV² - RV²) across expirations.
Signal = VRP momentum (short-term VRP change) as predictor of forward returns.
Positive VRP momentum = rising fear premium = potential mean-reversion signal.
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


def compute_rv(hist, window=20):
    """Compute realized volatility from daily returns."""
    returns = hist['Close'].pct_change().dropna()
    if len(returns) < window:
        return np.nan
    rv = returns.rolling(window).std().iloc[-1] * np.sqrt(252)
    return rv


def compute_vrp_metrics(ticker_str):
    """Compute VRP momentum metrics for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)

        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            return None

        # Get historical data for RV
        hist = tq.history(period="60d")
        if len(hist) < 30:
            return None
        rv_20d = compute_rv(hist, window=20)

        # Get option chains - focus on near-term expirations (7-45 DTE)
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 7 <= dte <= 45:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None

        results = []
        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                calls = chain.calls
                puts = chain.puts

                # Filter liquid options
                calls = calls[
                    (calls['volume'] > 10) | (calls['openInterest'] > 100)
                ].copy()
                puts = puts[
                    (puts['volume'] > 10) | (puts['openInterest'] > 100)
                ].copy()

                if len(calls) < 5 or len(puts) < 5:
                    continue

                # Get ATM IV (median of strikes within ±2% moneyness)
                all_opts = pd.concat([calls, puts], ignore_index=True)
                all_opts['volume'] = all_opts['volume'].fillna(0)
                all_opts['openInterest'] = all_opts['openInterest'].fillna(0)

                moneyness = all_opts['strike'] / current_price
                atm_opts = all_opts[
                    (moneyness >= 0.98) & (moneyness <= 1.02) &
                    (all_opts['impliedVolatility'].notna()) &
                    (all_opts['impliedVolatility'] > 0.01) &
                    (all_opts['impliedVolatility'] < 3.0)
                ]

                if len(atm_opts) < 3:
                    continue

                atm_iv = atm_opts['impliedVolatility'].median()

                # VRP = IV² - RV² (variance risk premium)
                vrp = atm_iv**2 - rv_20d**2 if pd.notna(rv_20d) else np.nan

                results.append({
                    'expiration': exp_str,
                    'dte': dte,
                    'atm_iv': atm_iv,
                    'rv_20d': rv_20d,
                    'vrp': vrp,
                })
            except Exception:
                continue

        if not results:
            return None

        df = pd.DataFrame(results)
        df = df.sort_values('dte')

        # Compute VRP momentum: change in VRP across near-term expirations
        # Short-term VRP (nearest expiration) vs slightly longer
        near_vrp = df.iloc[0]['vrp'] if len(df) > 0 else np.nan
        mid_vrp = df.iloc[1]['vrp'] if len(df) > 1 else np.nan
        far_vrp = df.iloc[-1]['vrp'] if len(df) > 2 else np.nan

        # VRP momentum = near VRP - mid VRP (positive = VRP rising near-term)
        vrp_momentum = near_vrp - mid_vrp if pd.notna(near_vrp) and pd.notna(mid_vrp) else np.nan
        vrp_term_slope = (far_vrp - near_vrp) / (df.iloc[-1]['dte'] - df.iloc[0]['dte']) if len(df) > 1 and pd.notna(near_vrp) and pd.notna(far_vrp) else np.nan

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'rv_20d': round(rv_20d, 4) if pd.notna(rv_20d) else np.nan,
            'near_vrp': round(near_vrp, 6) if pd.notna(near_vrp) else np.nan,
            'mid_vrp': round(mid_vrp, 6) if pd.notna(mid_vrp) else np.nan,
            'far_vrp': round(far_vrp, 6) if pd.notna(far_vrp) else np.nan,
            'vrp_momentum': round(vrp_momentum, 6) if pd.notna(vrp_momentum) else np.nan,
            'vrp_term_slope': round(vrp_term_slope, 8) if pd.notna(vrp_term_slope) else np.nan,
            'n_expirations': len(df),
            'vrp_by_dte': df.to_dict('records'),
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 VRP Momentum Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_vrp_metrics(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  RV (20d):       {r['rv_20d']:.4f}")
        print(f"  Near VRP:       {r['near_vrp']:.6f}")
        print(f"  Mid VRP:        {r['mid_vrp']:.6f}")
        print(f"  VRP Momentum:   {r['vrp_momentum']:.6f}")
        print(f"  VRP Term Slope: {r['vrp_term_slope']:.8f}")
        print(f"  Expirations:    {r['n_expirations']}")

    # Save detailed data
    os.makedirs("data", exist_ok=True)
    path = "data/vrp_momentum_latest.csv"

    # Flatten for CSV
    flat_rows = []
    for r in results:
        for exp_data in r['vrp_by_dte']:
            flat_rows.append({
                'ticker': r['ticker'],
                'current_price': r['current_price'],
                'expiration': exp_data['expiration'],
                'dte': exp_data['dte'],
                'atm_iv': exp_data['atm_iv'],
                'rv_20d': exp_data['rv_20d'],
                'vrp': exp_data['vrp'],
            })

    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved detailed data to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")