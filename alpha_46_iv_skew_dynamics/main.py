#!/usr/bin/env python3
"""Cross-sectional IV skew (25Δ put-call) rank — alpha_46.

Signal: cross-sectional cross-sectional percentile rank of the 25Δ put-call IV
skew (put_25d_iv - call_25d_iv) across the live option-chain universe.

Rationale: skew level cross-sectionally ranks fear/greed across large-cap
equities. Extreme skew = hedging/positioning crowdedness -> potential reversal.

This is the FIRST live-snapshot signal in this repo that is purely cross-sectional
(level rank, no time series), so it adds a fresh orthogonal dimension vs the
momentum/slope/percentile alphas (12, 13, 02, 05, 43).
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

RISK_FREE = 0.04
NEAR_DTE, FAR_DTE = 30, 75
MIN_DTE = 7


def bs_delta(spot, strike, dte, iv, option_type='call', r=RISK_FREE):
    t = max(dte, 1) / 365.0
    d1 = (np.log(spot / strike) + (r + 0.5 * iv ** 2) * t) / (iv * np.sqrt(t))
    n_d1 = 0.5 * (1 + erf(d1 / np.sqrt(2)))
    return n_d1 if option_type == 'call' else n_d1 - 1


def get_iv_at_delta(chain_df, current_price, dte, target_delta, option_type):
    if option_type == 'put':
        candidates = chain_df[chain_df['strike'] < current_price].copy()
    else:
        candidates = chain_df[chain_df['strike'] > current_price].copy()
    if len(candidates) < 2:
        return np.nan
    candidates['abs_delta'] = [
        abs(bs_delta(current_price, k, dte, v, option_type)) for k, v in zip(candidates['strike'], candidates['impliedVolatility'])
    ]
    candidates = candidates.sort_values('abs_delta')
    d = candidates['abs_delta'].values
    if d.min() > target_delta:
        idx = d.argmin()
        return float(candidates.iloc[idx]['impliedVolatility'])
    if d.max() < target_delta:
        idx = d.argmax()
        return float(candidates.iloc[idx]['impliedVolatility'])
    return float(np.interp(target_delta, d, candidates['impliedVolatility'].values))


def compute_skew(ticker_str):
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        now = datetime.now()
        valid = []
        for e in list(tq.options):
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d.date() - now.date()).days
                if MIN_DTE <= dte <= 180:
                    valid.append((d, dte))
            except ValueError:
                continue
        if not valid:
            return None
        targets = []
        for target in (NEAR_DTE, FAR_DTE):
            best = min(valid, key=lambda x: abs(x[1] - target))
            if best not in targets:
                targets.append(best)
        valid = sorted(targets, key=lambda x: x[0])
        skews = []
        for exp_date, dte in valid:
            try:
                chain = tq.option_chain(exp_date.strftime("%Y-%m-%d"))
                calls = chain.calls
                puts = chain.puts

                def _liquid(df):
                    return df[
                        ((df['volume'].fillna(0) > 10) | (df['openInterest'].fillna(0) > 100)) &
                        (df['impliedVolatility'].notna()) &
                        (df['impliedVolatility'] > 0.01) &
                        (df['impliedVolatility'] < 3.0) &
                        (df['lastPrice'] > 0)
                    ].copy()
                calls = _liquid(calls)
                puts = _liquid(puts)
                if len(calls) < 5 or len(puts) < 5:
                    continue
                put_25 = get_iv_at_delta(puts, current_price, dte, 0.25, 'put')
                call_25 = get_iv_at_delta(calls, current_price, dte, 0.25, 'call')
                if np.isnan(put_25) or np.isnan(call_25):
                    continue
                skews.append({'expiration': exp_date.strftime("%Y-%m-%d"), 'dte': dte, 'skew_25d': put_25 - call_25})
            except Exception as e:
                print(f"  ⚠️ {ticker_str} {exp_date}: {e}")
                continue
        if not skews:
            return None
        near = min(skews, key=lambda x: abs(x['dte'] - NEAR_DTE))
        far = max(skews, key=lambda x: x['dte'])
        return {
            'ticker': ticker_str,
            'current_price': round(float(current_price), 2),
            'near_skew_25d': round(float(near['skew_25d']), 4),
            'far_skew_25d': round(float(far['skew_25d']), 4),
            'skew_25d': round(float(near['skew_25d']), 4),
            'n_expirations': len(skews),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 IV Skew (25Δ) Cross-Sectional Rank — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    results = [r for r in (compute_skew(t) for t in TICKERS) if r]
    if not results:
        print("No data collected.")
        sys.exit(1)
    df = pd.DataFrame(results)
    df['skew_rank'] = df['skew_25d'].rank(ascending=False, pct=True)  # 1.0 = extreme fear
    df = df.sort_values('skew_rank', ascending=False)
    print(df.to_string(index=False))
    os.makedirs("data", exist_ok=True)
    path = "data/iv_skew_dynamics_46_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run")
