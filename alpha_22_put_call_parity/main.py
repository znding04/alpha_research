#!/usr/bin/env python3
"""Put-Call Parity Residual Alpha Signal (alpha_22)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd, yfinance as yf
from datetime import datetime
from common.universe import TICKERS

LIQ_VOLUME = 10
LIQ_OI = 100
TARGET_DTE = (14, 60)

def get_risk_free_rate():
    try:
        irx = yf.Ticker("^IRX").history(period="5d")["Close"]
        return float(irx.iloc[-1]) / 100.0 if not irx.empty else 0.045
    except Exception:
        return 0.045

def _liquid(df):
    df = df.copy()
    df['volume'] = df['volume'].fillna(0).astype(float)
    df['openInterest'] = df['openInterest'].fillna(0).astype(float)
    df['impliedVolatility'] = df['impliedVolatility'].fillna(np.nan)
    has_quote = (df['bid'].notna()) & (df['ask'].notna()) & (df['bid'] > 0) & (df['ask'] > 0)
    df['mid'] = np.where(has_quote, (df['bid'] + df['ask']) / 2.0, df['lastPrice'].fillna(0.0))
    return df[
        ((df['volume'] > LIQ_VOLUME) | (df['openInterest'] > LIQ_OI))
        & (df['impliedVolatility'].notna())
        & (df['impliedVolatility'] > 0.01)
        & (df['impliedVolatility'] < 3.0)
        & (df['mid'] > 0)
    ].copy()

def compute_parity(ticker_str, r=0.045):
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info or {}
        spot = info.get('currentPrice') or info.get('regularMarketPrice')
        if spot is None or spot <= 0:
            return None
        div_yield = float(info.get('dividendYield') or 0.0)
        now = datetime.now()
        exp_str = None; best_dte = None
        for e_str in (tq.options or []):
            try:
                d = datetime.strptime(e_str, "%Y-%m-%d")
                dte = (d - now).days
                if TARGET_DTE[0] <= dte <= TARGET_DTE[1]:
                    best_dte, exp_str = dte, e_str
            except ValueError:
                continue
        if exp_str is None:
            options = list(tq.options or [])
            if not options: return None
            exp_str = options[0]
            best_dte = (datetime.strptime(exp_str, "%Y-%m-%d") - now).days
        chain = tq.option_chain(exp_str)
        calls, puts = _liquid(chain.calls), _liquid(chain.puts)
        if calls.empty or puts.empty:
            return None
        common_strikes = sorted(set(calls['strike']) & set(puts['strike']))
        # Compute median parity across common strikes
        residuals = []
        for K in common_strikes:
            c_row = calls[calls['strike'] == K].sort_values('volume', ascending=False).iloc[0]
            p_row = puts[puts['strike'] == K].sort_values('volume', ascending=False).iloc[0]
            C, P = float(c_row['mid']), float(p_row['mid'])
            T = max(best_dte or 14, 1) / 252.0
            parity = C - P - (spot - float(K) * np.exp(-(r - div_yield) * T))
            bps = (parity / spot) * 10000.0 if spot > 0 else np.nan
            if pd.notna(bps):
                residuals.append(bps)
        if not residuals:
            return None
        median_bps = float(np.median(residuals))
        # Reference strike nearest to spot
        nearest_K = float(min(common_strikes, key=lambda k: abs(k - spot)))
        # Mid and IV at reference strike
        c_row_ref = None; p_row_ref = None
        try:
            c_row_ref = calls[calls['strike']==nearest_K].sort_values('volume', ascending=False).iloc[0]
            p_row_ref = puts[puts['strike']==nearest_K].sort_values('volume', ascending=False).iloc[0]
        except Exception:
            pass
        return {
            'ticker': ticker_str,
            'current_price': round(spot, 2),
            'strike': nearest_K,
            'dte': int(best_dte) if best_dte else None,
            'call_mid': round(float(c_row_ref['mid']), 4) if c_row_ref is not None else None,
            'put_mid': round(float(p_row_ref['mid']), 4) if p_row_ref is not None else None,
            'call_iv': round(float(c_row_ref['impliedVolatility']), 4) if c_row_ref is not None else None,
            'put_iv': round(float(p_row_ref['impliedVolatility']), 4) if p_row_ref is not None else None,
            'dividend_yield': round(div_yield, 4),
            'parity_raw': None,
            'parity_bps': round(median_bps, 2),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None

if __name__ == "__main__":
    print(f"\n📊 Put-Call Parity Residual (alpha_22) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    rate = get_risk_free_rate()
    print(f"Risk-free rate: {rate:.4f} (13-week T-bill, ^IRX)")
    results = []
    for t in TICKERS:
        r = compute_parity(t, rate)
        if r:
            results.append(r)
            b = r['parity_bps']
            tag = "📉 HARD-TO-BORROW (short bias)" if b > 20 else ("📈 CALL RICH" if b < -20 else "⚡ near parity")
            print(f"\n{r['ticker']:>6}  px={r['current_price']:>8}  K={r['strike']:>7}  DTE={r['dte']:>3}  "
                  f"resid={b:>7} bps  {tag}")
    if not results:
        print("No data collected.")
        exit(1)
    df = pd.DataFrame(results)
    os.makedirs("data", exist_ok=True)
    path = "data/alpha_22_put_call_parity_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}  ({len(df)} tickers)")
    print("\nRanked by residual (positive = hard-to-borrow / short bias):")
    ranked = df.sort_values('parity_bps', ascending=False)
    for _, r in ranked.iterrows():
        print(f"  {r['ticker']:>6} {r['parity_bps']:>8} bps  px={r['current_price']:>7} K={r['strike']:>7} DTE={r['dte']:>3}")