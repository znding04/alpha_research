#!/usr/bin/env python3
"""VRP Change (alpha_21_vrp) — Daily change in Variance Risk Premium.

Signals from current + previous-day VRP. Uses data/vrp_change_history.json
for historical VRP tracking (same pattern as alpha_12 IV momentum).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, yfinance as yf
from datetime import datetime
from common.universe import TICKERS

HISTORY_FILE = "data/vrp_change_history.json"

def get_nearest_exp(tq, min_dte=7, max_dte=60):
    try:
        exps = list(tq.options)
        now = datetime.now()
        valid = []
        for e in exps:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if min_dte <= dte <= max_dte:
                    valid.append((d, dte))
            except ValueError:
                continue
        valid.sort(key=lambda x: x[0])
        return valid[0][0].strftime("%Y-%m-%d") if valid else None
    except Exception:
        return None

def get_robust_atm_iv(tq, price, exp_str):
    try:
        chain = tq.option_chain(exp_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        df['volume'] = df['volume'].fillna(0)
        df['openInterest'] = df['openInterest'].fillna(0)
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.05) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()
        if len(df) < 10:
            return None
        moneyness = df['strike'] / price
        atm = df[(moneyness >= 0.98) & (moneyness <= 1.02)]
        if len(atm) >= 3:
            return atm['impliedVolatility'].median()
        else:
            vs = df[df['impliedVolatility'] > 0.05]
            if len(vs) == 0:
                return None
            idx = (vs['strike'] - price).abs().idxmin()
            return vs.loc[idx, 'impliedVolatility']
    except Exception:
        return None

def compute_rv(ticker_str, lookback=30):
    try:
        hist = yf.Ticker(ticker_str).history(period=f"{lookback + 15}d")
        close = hist['Close']
        log_ret = np.log(close / close.shift(1)).dropna()
        if len(log_ret) < lookback:
            return np.nan
        rv = log_ret.iloc[-lookback:].std() * np.sqrt(252)
        return rv if pd.notna(rv) and rv > 0 else np.nan
    except Exception:
        return np.nan

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE) as f:
            return __import__('json').load(f)
    return {}

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        __import__('json').dump(history, f, indent=2)

def compute_snapshot():
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    results = []
    for t in TICKERS:
        try:
            tq = yf.Ticker(t)
            info = tq.info
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            if price is None or price <= 0:
                continue
            exp_str = get_nearest_exp(tq)
            if exp_str is None:
                continue
            iv = get_robust_atm_iv(tq, price, exp_str)
            if iv is None or iv <= 0.01:
                continue
            rv_val = compute_rv(t)
            if pd.isna(rv_val) or rv_val <= 0:
                continue
            vrp = iv**2 - rv_val**2
            if t not in history:
                history[t] = []
            # Keep last 20 days
            history[t].append({'date': today, 'vrp': float(vrp), 'iv': float(iv), 'rv': float(rv_val)})
            history[t] = history[t][-20:]
            # Compute change vs previous entry (if exists and previous date)
            change = np.nan
            if len(history[t]) >= 2:
                prev_vrp = history[t][-2]['vrp']
                change = float(vrp - prev_vrp)
            results.append({
                'ticker': t,
                'price': round(price, 2),
                'iv': round(iv, 4),
                'rv': round(rv_val, 4),
                'vrp': round(vrp, 6),
                'vrp_change_1d': round(change, 4) if not np.isnan(change) else np.nan,
                'exp_str': exp_str,
            })
        except Exception as e:
            print(f"  ⚠️ {t}: {e}")
    save_history(history)
    return pd.DataFrame(results)

if __name__ == '__main__':
    print(f"\n📈 VRP Change (alpha_21_vrp) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    df = compute_snapshot()
    if df.empty:
        print("No data collected.")
        exit(1)
    print(df.to_string(index=False))
    print("\n💡 Interpretation: Positive change = VRP rising (fear increasing); Negative = VRP falling (complacency).")
    os.makedirs('data', exist_ok=True)
    df.to_csv('data/vrp_change_latest.csv', index=False)
    print(f"\n✅ Saved to data/vrp_change_latest.csv")
