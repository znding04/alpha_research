#!/usr/bin/env python3
"""IV Skew Dynamics alpha signal — put-call skew at ~30d / ~75d DTE (OTM put vs OTM call IV)."""
import os, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, yfinance as yf
from datetime import datetime
from common.universe import TICKERS

def compute_skew(ticker_str):
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        price = info.get('currentPrice') or info.get('regularMarketPrice')
        if price is None or price <= 0: return None
        exp_strs = list(tq.options)
        now = datetime.now()
        valid = []
        for e in exp_strs:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                if d.date() > now.date() and (d-now).days <= 180:
                    valid.append((d, e, (d-now).days))
            except ValueError: continue
        # Pick near (~25-35 DTE) and far (~65-85 DTE)
        near = [v for v in valid if 25 <= v[2] <= 35]
        far = [v for v in valid if 65 <= v[2] <= 85]
        if not near or not far: return None
        near.sort(key=lambda x: x[2]); far.sort(key=lambda x: x[2])
        near_str = near[0][1]; far_str = far[0][1]
        def sk(exp_str):
            chain = tq.option_chain(exp_str)
            # add putCall before concat
            calls = chain.calls.copy(); calls['putCall'] = 'C'
            puts = chain.puts.copy(); puts['putCall'] = 'P'
            df = pd.concat([calls, puts], ignore_index=True)
            df['volume'] = df['volume'].fillna(0).astype(int)
            df['openInterest'] = df['openInterest'].fillna(0).astype(int)
            df = df[
                ((df['volume'] > 10) | (df['openInterest'] > 100)) &
                df['impliedVolatility'].notna() &
                (df['impliedVolatility'] > 0.01) & (df['impliedVolatility'] < 3.0) &
                (df['lastPrice'] > 0)
            ].copy()
            if len(df) < 10: return None, 0
            put_target = price * 0.90
            call_target = price * 1.10
            put_df = df[(df['strike'] < price) & (df['putCall'] == 'P')]
            call_df = df[(df['strike'] > price) & (df['putCall'] == 'C')]
            put_iv = put_df.loc[(put_df['strike']-put_target).abs().idxmin(), 'impliedVolatility'] if not put_df.empty else np.nan
            call_iv = call_df.loc[(call_df['strike']-call_target).abs().idxmin(), 'impliedVolatility'] if not call_df.empty else np.nan
            if pd.isna(put_iv) or pd.isna(call_iv): return None, len(df)
            skew = float(put_iv) - float(call_iv)
            return round(skew, 4), len(df)
        s_near, n_near = sk(near_str)
        s_far, n_far = sk(far_str)
        if s_near is None or s_far is None: return None
        signal = round(s_far - s_near, 4)  # term slope of skew + implicit level signal
        return {'ticker': ticker_str, 'price': round(price,2),
                'skew_30d': s_near, 'skew_75d': s_far, 'signal': signal,
                'n_near': n_near, 'n_far': n_far, 'near_exp': near_str, 'far_exp': far_str}
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None

if __name__ == "__main__":
    print(f"\n🔍 IV Skew Dynamics — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*70)
    results = []
    for t in TICKERS:
        r = compute_skew(t)
        if r: results.append(r)
    if not results: print("No data."); exit(1)
    df = pd.DataFrame(results)
    df = df.sort_values('signal', ascending=False)
    print(df[['ticker','price','skew_30d','skew_75d','signal','near_exp','far_exp']].to_string(index=False))
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/iv_skew_dynamics_latest.csv', index=False)
    print(f"\n✅ Saved data/iv_skew_dynamics_latest.csv  | tickers={len(df)}")
    print("💡 Signal > 0 → long-dated skew exceeds short-dated → vol-of-vol rising (expect vol spike)\n")