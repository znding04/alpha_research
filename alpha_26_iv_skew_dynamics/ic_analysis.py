#!/usr/bin/env python3
"""IC analysis for alpha_26: cross-sectional rank IC of IV skew signal vs next-21-day forward return."""
import os, sys, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, yfinance as yf
from common.universe import TICKERS

path = 'data/iv_skew_dynamics_latest.csv'
if not os.path.exists(path):
    print(f"⚠️ {path} not found — run main.py first"); sys.exit(0)
LR = pd.read_csv(path)
os.makedirs('data', exist_ok=True)

returns = {}
for t in TICKERS:
    try:
        px = yf.Ticker(t).history(period='252d', auto_adjust=True)
        if px is not None and len(px) >= 30 and 'Close' in px.columns:
            c = px['Close']
            ret_21d = float(c.iloc[-1] / c.iloc[-22] - 1)
            returns[t] = ret_21d
    except Exception as e:
        print(f"  ⚠️ {t}: {e}")
rets = pd.Series(returns).loc[lambda s: s.index.isin(LR['ticker'])]
sig = LR.set_index('ticker')['signal'].reindex(rets.index)
if len(sig) < 5:
    print(f"⚠️ too few tickers with data ({len(sig)})"); sys.exit(0)
icc = sig.corr(rets)
top = sig.sort_values(ascending=False).head(max(1, int(len(sig)*0.3))).index
bot = sig.sort_values(ascending=True).head(max(1, int(len(sig)*0.3))).index
top_ret = rets.loc[top].mean(); bot_ret = rets.loc[bot].mean()
print(f"Tickers with data: {len(sig)}")
print(f"Cross-sectional IC (rank signal vs next 21d return): {icc:.4f}")
print(f"Long-top-30% return: {top_ret:+.4%} | Short-bottom-30% return: {bot_ret:+.4%} | L-S: {(top_ret-bot_ret):+.4%}")
with open('data/iv_skew_dynamics_ic.txt','w') as f:
    f.write(f"Tickers: {len(sig)}\nIC: {icc:.4f}\nTop30: {top_ret:+.4%}\nBot30: {bot_ret:+.4%}\nL-S: {(top_ret-bot_ret):+.4%}\n")
print("Saved data/iv_skew_dynamics_ic.txt")