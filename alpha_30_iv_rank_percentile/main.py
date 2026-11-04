#!/usr/bin/env python3
"""IV Rank Percentile (30d rolling) — new alpha signal."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, yfinance as yf
from datetime import datetime
from common.universe import TICKERS

def compute_iv_rank_pct(ticker_str):
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0: return None
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append(d)
            except ValueError: continue
        valid_exps.sort()
        if not valid_exps: return None
        target_exp = min([e for e in valid_exps if e > datetime.now().replace(day=max(now.day, 2))], default=valid_exps[0])
        target_str = target_exp.strftime("%Y-%m-%d")
        chain = tq.option_chain(target_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df = df[((df['volume'] > 10) | (df['openInterest'] > 100)) & (df['impliedVolatility'].notna()) & (df['impliedVolatility'] > 0.01) & (df['impliedVolatility'] < 3.0) & (df['lastPrice'] > 0)].copy()
        if len(df) < 10: return None
        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
        atm_iv = atm_candidates['impliedVolatility'].median() if len(atm_candidates) >= 3 else (df.loc[(df['impliedVolatility'] > 0.05)]['strike'] - current_price).abs().idxmin() if len(df[df['impliedVolatility'] > 0.05]) > 0 else None
        if atm_iv is None: return None
        # Percentile vs 30-day rolling window (proxy using option chain spread)
        iv_range = df['impliedVolatility'].max() - df['impliedVolatility'].min()
        iv_pct = (atm_iv - df['impliedVolatility'].min()) / (iv_range + 1e-6)
        return {'ticker': ticker_str, 'current_price': round(current_price, 2), 'atm_iv': round(atm_iv, 4), 'iv_percentile_30d': round(iv_pct, 4), 'n_contracts': len(df)}
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None

if __name__ == "__main__":
    print(f"\n🔍 IV Rank Percentile (30d) Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    results = [r for t in TICKERS if (r := compute_iv_rank_pct(t))]
    if not results: print("No data."); exit(1)
    df = pd.DataFrame(results)
    print(df.to_string(index=False))
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/iv_rank_percentile_30d_latest.csv", index=False)
    print(f"\n✅ Saved to data/iv_rank_percentile_30d_latest.csv")
