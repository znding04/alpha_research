#!/usr/bin/env python3
"""Alpha 39 — VRP (Variance Risk Premium) with EWMA-vol Forecast.

Signal: VRP = IV^2 - E[RV_ewma]^2

Where IV is ATM implied volatility from the current option chain, and E[RV_ewma] is the
EWMA (RiskMetrics lambda=0.94) forecast of next ~30-day annualized realized volatility,
rather than a fixed trailing realized-vol window (e.g. 30d, 60d).

Why EWMA as the "realized vol" forecast:
  - Fixed trailing windows (alpha_04, alpha_20, alpha_21, alpha_23, alpha_30, alpha_33,
    alpha_34, alpha_36, alpha_38) lag the current vol regime; a trailing-window VRP
    therefore mixes last-30d realized vol with today-30d IV, inducing regime-lagged noise.
  - EWMA forecast re-estimates vol with weight decay lambda=0.94 (effective half-life
    ~6.2 trading days), giving a forward-looking realized-vol expectation that is closer
    in time to current ATM IV than a fixed 30-day window.

Interpretation:
  VRP_ewma > 0 -> IV^2 > E[RV]^2 -> positive variance risk premium, vol expensively priced,
              cross-sectionally => most-overpriced names (short vol / avoid)
  VRP_ewma < 0 -> IV^2 < E[RV]^2 -> vol cheaply priced, mean-reversion long / overweight

Cross-sectionally: rank tickers by VRP_ewma. Most positive = most complacent (overpriced vol).
Most negative = most fearful (underpriced vol).

Uses yfinance only — no paid APIs. Cross-section across tickers from common.universe.py.

Output: data/vrp_ewma_latest.csv
"""

import os
import sys
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from common.universe import TICKERS

EWMA_LAMBDA = 0.94          # RiskMetrics EWMA decay
RV_HORIZON_DAYS = 30        # annualized realized vol forecast horizon
IV_MIN = 0.01
IV_MAX = 3.0
MIN_ATM_STRIKE_IV = 0.05
RISK_FREE_RATE = 0.045      # ~4.5% annual
DIVIDEND_YIELD = 0.0        # simplified


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(imp_vol, S, K, T, r, q):
    """Black-Scholes call price."""
    if imp_vol <= 0:
        return np.nan
    sqrtT = np.sqrt(T) if T > 0 else 0.0
    d1 = np.log(S / K) + (r - q + 0.5 * imp_vol ** 2) * sqrtT / (imp_vol * sqrtT) if imp_vol > 0 else 0
    d2 = d1 - imp_vol * sqrtT
    price = (S * norm_cdf(d1) - K * np.exp(-r * T) * norm_cdf(d2)) * np.exp(-q * T)
    return price


def bs_implied_vol(S, K, T, r, q, mid_price, max_iter=200, tol=1e-8):
    """Solve ATM/ITM option IV via bisection on Black-Scholes price."""
    if np.isnan(mid_price) or mid_price <= 0 or T <= 0:
        return np.nan
    low, high = IV_MIN, IV_MAX
    mid = (low + high) / 2.0
    for _ in range(max_iter):
        if bs_price(mid, S, K, T, r, q) < mid_price:
            low = mid
        else:
            high = mid
        mid = (low + high) / 2.0
        if (high - low) < tol:
            break
    return float(mid)


def ewma_vol_forecast(closes, lambda_=EWMA_LAMBDA, days=RV_HORIZON_DAYS):
    """EWMA forecast of annualized realized volatility from daily closes."""
    if len(closes) < 60:
        return np.nan
    log_ret = np.log(closes / closes.shift(1)).dropna()
    if len(log_ret) < 30:
        return np.nan
    var = log_ret.var(ddof=1)
    alpha = 2.0 / (lambda_ + 1.0)
    prev_var = float(var) if pd.notna(var) else 0.0
    last_r2 = float(log_ret.iloc[-1] ** 2)
    v_next = (1 - alpha) * prev_var + alpha * last_r2
    return float(np.sqrt(max(v_next, 1e-12)) * np.sqrt(252))


def compute_vrp_ewma(ticker_str):
    """Compute VRP using EWMA-forecasted realized vol for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        current_price = float(current_price)

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

        # Prefer expiration with DTE >= 7 to avoid weekly noise
        min_dte_exp = [e for e in valid_exps if (e.date() - now.date()).days >= 7]
        if min_dte_exp:
            target_exp = min_dte_exp[0]
        else:
            target_exp = valid_exps[0]

        chain = tq.option_chain(target_exp.strftime("%Y-%m-%d"))
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        # Fix dtypes (numpy int64 volume/OI may hold NaN/inf)
        for df in (calls, puts):
            df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
            df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)

        # Filter calls: liquid + positive lastPrice (yfinance IV is unreliable; we recover IV from prices via BS)
        calls = calls[
            ((calls['volume'] > 10) | (calls['openInterest'] > 100)) &
            (calls['lastPrice'] > 0)
        ].copy()

        if len(calls) == 0:
            return None

        # Get ATM call: strike closest to current_price
        calls['moneyness'] = calls['strike'] / current_price
        atm_calls = calls[(calls['moneyness'] >= 0.98) & (calls['moneyness'] <= 1.02) & (calls['lastPrice'] > 0)].copy()
        if len(atm_calls) == 0:
            return None
        atm_calls['atm_diff'] = (atm_calls['strike'] - current_price).abs()
        atm_calls = atm_calls.sort_values('atm_diff')
        atm_strike = float(atm_calls.iloc[0]['strike'])
        bid = float(atm_calls.iloc[0]['bid']) if pd.notna(atm_calls.iloc[0]['bid']) else 0.0
        ask = float(atm_calls.iloc[0]['ask']) if pd.notna(atm_calls.iloc[0]['ask']) else 0.0
        mid_price = float((bid + ask) / 2.0) if (bid > 0 and ask > 0) else float(atm_calls.iloc[0]['lastPrice'])
        atm_mid = float(mid_price)

        # Time to expiry in years
        exp_date = datetime.strptime(str(target_exp.date()), '%Y-%m-%d')
        T = max((exp_date - now).days / 365.0, 0.01)

        # Solve IV from mid price via Black-Scholes call bisection
        atm_iv = bs_implied_vol(current_price, atm_strike, T, RISK_FREE_RATE, DIVIDEND_YIELD, atm_mid)
        if np.isnan(atm_iv) or atm_iv <= 0 or atm_iv > IV_MAX:
            return None

        # EWMA forecast realized vol from daily closes
        hist = tq.history(period="6mo", interval="1d")
        close = hist['Close'].dropna()
        ewma_rv = ewma_vol_forecast(close)
        if np.isnan(ewma_rv) or ewma_rv <= 0:
            return None

        vrp = atm_iv ** 2 - ewma_rv ** 2

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'iv_atm': round(float(atm_iv), 4),
            'rv_ewma_30d': round(float(ewma_rv), 4),
            'vrp': round(float(vrp), 6),
            'vrp_pct': round(float(vrp) / (float(ewma_rv) ** 2) * 100, 2),
            'n_contracts': int(len(calls)),
        }
    except Exception as e:
        print(f"  [WARN] {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\nVRP (EWMA forecast) Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_vrp_ewma(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df.to_string(index=False))

    # Print interpretation
    for _, r in df.iterrows():
        v = r['vrp']
        if v > 0:
            print(f"\n{r['ticker']}: VRP > 0 (expensive vol) — IV {r['iv_atm']:.4f} > EWMA-RV {r['rv_ewma_30d']:.4f}")
        else:
            print(f"\n{r['ticker']}: VRP < 0 (cheap vol) — IV {r['iv_atm']:.4f} < EWMA-RV {r['rv_ewma_30d']:.4f}")

    os.makedirs("data", exist_ok=True)
    path = "data/vrp_ewma_latest.csv"
    df.to_csv(path, index=False)
    print(f"\nOK Saved to {path}")
    print(f"   Tickers: {len(df)}\n")
