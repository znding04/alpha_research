#!/usr/bin/env python3
"""IV Skew Dynamics alpha signal — put-call IV skew over time.

Signal: skew = ATM_put_iv - ATM_call_iv (same moneyness band, same expiration).

Interpretation:
  skew > 0 → puts more expensive than calls (tail-hedge demand, downside fear)
  skew < 0 → calls more expensive than puts (upside speculation, complacency)

Cross-sectionally: rank tickers by skew. Most positive = most defensive
(tail protection bid). Most negative = most complacent (upside speculation).

The "dynamics" angle: skew is not static — it shifts with market regime. A
rising skew (puts getting more expensive) often precedes equity drawdowns, so
skew change can be a forward-looking signal.

Uses yfinance only — no paid APIs. Cross-section across 16 tickers.
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

MIN_LIQUID_VOLUME = 10
MIN_LIQUID_OI = 100
MIN_OPS = 10
MONEYNESS_BAND = 0.02   # ±2% around ATM for skew measurement
MIN_IV = 0.05           # reject placeholder/near-zero IVs
MAX_IV = 3.0


def _clean_chain(df):
    """Filter an option chain (calls or puts) for liquidity and sane IV."""
    df = df.copy()
    df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
    df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
    return df[
        ((df['volume'] > MIN_LIQUID_VOLUME) | (df['openInterest'] > MIN_LIQUID_OI)) &
        (df['impliedVolatility'].notna()) &
        (df['impliedVolatility'] > MIN_IV) &
        (df['impliedVolatility'] < MAX_IV) &
        (df['lastPrice'] > 0)
    ].copy()


def _atm_iv_from_chain(chain_df, current_price, side):
    """Median IV of liquid strikes within ±2% moneyness, side-specific.

    Returns NaN if fewer than 2 candidates survive the filter.
    """
    if len(chain_df) == 0:
        return np.nan
    moneyness = chain_df['strike'] / current_price
    band = chain_df[(moneyness >= 1 - MONEYNESS_BAND) & (moneyness <= 1 + MONEYNESS_BAND)]
    if len(band) < 2:
        # Fallback: single closest strike
        valid = chain_df[chain_df['impliedVolatility'] > MIN_IV]
        if len(valid) == 0:
            return np.nan
        idx = (valid['strike'] - current_price).abs().idxmin()
        return float(valid.loc[idx, 'impliedVolatility'])
    return float(band['impliedVolatility'].median())


def compute_skew(ticker_str, target_dte=30, dte_window=15):
    """Compute put-call IV skew for a single ticker at a fixed tenor.

    Returns dict with skew = put_iv - call_iv, plus components.
    """
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None

        expirations = list(tq.options)
        now = datetime.now()
        best_exp = None
        best_dte = None
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d.date() - now.date()).days
                if dte > 0 and abs(dte - target_dte) <= dte_window:
                    if best_dte is None or abs(dte - target_dte) < abs(best_dte - target_dte):
                        best_exp = e
                        best_dte = dte
            except ValueError:
                continue

        if best_exp is None:
            return None

        chain = tq.option_chain(best_exp)
        calls = _clean_chain(chain.calls)
        puts = _clean_chain(chain.puts)

        call_iv = _atm_iv_from_chain(calls, current_price, 'call')
        put_iv = _atm_iv_from_chain(puts, current_price, 'put')

        if np.isnan(call_iv) or np.isnan(put_iv):
            return None

        skew = put_iv - call_iv
        skew_pct = skew * 100  # in percentage points of IV

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'dte': int(best_dte),
            'expiration': best_exp,
            'call_atm_iv': round(call_iv, 4),
            'put_atm_iv': round(put_iv, 4),
            'iv_skew': round(skew, 4),
            'iv_skew_pct': round(skew_pct, 2),
            'n_calls': int(len(calls)),
            'n_puts': int(len(puts)),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📉 IV Skew Dynamics — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Signal: put_atm_iv - call_atm_iv (ATM ±{MONEYNESS_BAND*100:.0f}%, ~{30} DTE)")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_skew(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df[['ticker', 'current_price', 'dte', 'call_atm_iv', 'put_atm_iv',
              'iv_skew', 'iv_skew_pct', 'n_calls', 'n_puts']].to_string(index=False))
    print("\n💡 Interpretation:")
    print("   iv_skew > 0 → puts more expensive than calls (tail-hedge demand, downside fear)")
    print("   iv_skew < 0 → calls more expensive than puts (upside speculation, complacency)")

    os.makedirs("data", exist_ok=True)
    path = "data/iv_skew_dynamics_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")