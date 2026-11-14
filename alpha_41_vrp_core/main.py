#!/usr/bin/env python3
"""VRP Core (IV² − RV²) cross-sectional alpha for the core 6 tickers.

Signal: Variance Risk Premium = IV² − RV² where
  - IV = ATM implied volatility from the nearest liquid option chain
  - RV = trailing 252-day annualized realized volatility from daily closes

Interpretation:
  VRP > 0 → options expensive (implied > realized) → vol risk premium
  VRP < 0 → options cheap (implied < realized) → vol underpriced / stress

Cross-sectionally: rank tickers by VRP. High VRP = expensive vol; low VRP = cheap vol.
Hypothesis: the cross-sectional rank of VRP predicts forward returns over 5–21 days.
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


def get_atm_iv(ticker_str, target_dte_range=(14, 90)):
    """ATM IV from the nearest liquid expiration within target DTE range.

    Returns (atm_iv, current_price) or (None, None) on failure.
    """
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
                if target_dte_range[0] <= dte <= target_dte_range[1]:
                    valid_exps.append(d)
            except ValueError:
                continue
        valid_exps.sort()
        if not valid_exps:
            return None, None

        target_exp = min(
            [e for e in valid_exps if e > datetime.now().replace(day=max(now.day, 2))],
            default=valid_exps[0],
        )
        target_str = target_exp.strftime("%Y-%m-%d")

        chain = tq.option_chain(target_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # Fix dtypes: volume/OI are numpy int64, comparison fails on NaN/inf.
        # Fix: fillna(0) first, then .astype(int) for proper integer comparison.
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
            return None, None

        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]

        if len(atm_candidates) >= 3:
            atm_iv = atm_candidates['impliedVolatility'].median()
        else:
            valid_strikes = df[df['impliedVolatility'] > 0.05]
            if len(valid_strikes) == 0:
                return None, None
            atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
            atm_iv = valid_strikes.loc[atm_idx, 'impliedVolatility']

        median_iv = df['impliedVolatility'].median()
        iv_spread = atm_iv - median_iv

        return round(atm_iv, 4), round(current_price, 2), round(median_iv, 4), round(iv_spread, 4), len(df)

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None, None


def compute_rv(ticker_str, window=252):
    """Trailing annualized realized volatility from daily closes."""
    try:
        hist = yf.Ticker(ticker_str).history(period="1y", interval="1d")
        if hist.empty or len(hist) < max(window // 2, 10):
            return None
        closes = hist['Close'].dropna()
        log_ret = np.log(closes / closes.shift(1)).dropna()
        rv = log_ret.rolling(window, min_periods=max(window // 2, 10)).std().iloc[-1] * np.sqrt(252)
        return float(rv)
    except Exception:
        return None


def compute_signal(ticker_str):
    """Return dict with VRP signal for a single ticker."""
    res = get_atm_iv(ticker_str)
    if res is None or res[0] is None:
        return None
    atm_iv, current_price, median_iv, iv_spread, n_contracts = res
    rv = compute_rv(ticker_str)
    if rv is None or rv <= 0:
        return None
    vrp = atm_iv**2 - rv**2
    vrp_ratio = vrp / rv**2 if rv > 0 else np.nan
    return {
        'ticker': ticker_str,
        'current_price': current_price,
        'atm_iv': atm_iv,
        'median_iv': median_iv,
        'iv_spread': iv_spread,
        'rv_252d': round(rv, 4),
        'vrp_variance': round(vrp, 6),
        'vrp_ratio': round(vrp_ratio, 4),
        'n_contracts': n_contracts,
    }


if __name__ == "__main__":
    print(f"\n🔍 VRP Core (IV² − RV²) Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_signal(t)
        if r:
            results.append(r)
            print(f"  ✅ {t}: VRP={r['vrp_variance']:.6f} (IV={r['atm_iv']:.4f}, RV={r['rv_252d']:.4f})")
        else:
            print(f"  ⚠️ {t}: no data")

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print("\n" + df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   VRP > 0 → options expensive (vol risk premium, fear)")
    print("   VRP < 0 → options cheap (vol underpriced, complacency)")
    print("   Cross-sectionally: high VRP → potential mean reversion / equity underperformance")

    os.makedirs("data", exist_ok=True)
    path = "data/vrp_core_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")
