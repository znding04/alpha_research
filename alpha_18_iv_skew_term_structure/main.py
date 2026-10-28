#!/usr/bin/env python3
"""Compute IV Skew-Term Structure Signal - Combine IV slope with skew dynamics."""
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

def get_skew_term_structure(ticker_str, exp_days_map):
    try:
        tq = yf.Ticker(ticker_str)
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
        if len(valid_exps) < 2:
            return None
        target_exps = []
        for exp_days, need_dte in exp_days_map.items():
            target = None
            for e in valid_exps:
                dte = (e.date() - now.date()).days
                if dte >= need_dte:
                    target = e
                    break
            if target:
                target_exps.append((exp_days, target))
        if len(target_exps) < 2:
            return None
        chains = {}
        for exp_days, exp_date in target_exps:
            target_str = exp_date.strftime("%Y-%m-%d")
            chain = tq.option_chain(target_str)
            df = pd.concat([chain.calls, chain.puts], ignore_index=True)
            df['volume'] = df['volume'].fillna(0).astype(int)
            df['openInterest'] = df['openInterest'].fillna(0).astype(int)
            df = df[
                ((df['volume'] > 10) | (df['openInterest'] > 100)) &
                (df['impliedVolatility'].notna()) &
                (df['impliedVolatility'] > 0.01) &
                (df['impliedVolatility'] < 3.0) &
                (df['lastPrice'] > 0)
            ].copy()
            chains[exp_days] = df
        return chains
    except Exception as e:
        print(f"  ⚠️ {ticker_str} (skew term): {e}")
        return None

def compute_iv_skew_term_signal(ticker_str):
    try:
        exp_days_map = {30: 30, 75: 75}
        result = get_skew_term_structure(ticker_str, exp_days_map)
        if not result:
            return None
        chains = result
        info = yf.Ticker(ticker_str).info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        atm_ivs = {}
        skew_values = {}
        for exp_days, df in chains.items():
            if len(df) < 10:
                continue
            moneyness = df['strike'] / current_price
            atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
            if len(atm_candidates) >= 3:
                atm_iv = atm_candidates['impliedVolatility'].median()
            else:
                valid_strikes = df[df['impliedVolatility'] > 0.05]
                if len(valid_strikes) == 0:
                    continue
                atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
                atm_iv = valid_strikes.loc[atm_idx, 'impliedVolatility']
            atm_ivs[exp_days] = atm_iv
            
            # Simple delta approximation for skew
            calls_df = df
            puts_df = df
            
            # Approximate 25d delta contracts using strike distance
            call_idx = (calls_df['strike'] - current_price).abs().idxmin()
            put_idx = (puts_df['strike'] - current_price).abs().idxmin()
            
            call_25d_iv = calls_df.loc[call_idx, 'impliedVolatility']
            put_25d_iv = puts_df.loc[put_idx, 'impliedVolatility']
            
            # Normalize skew
            avg_iv = (call_25d_iv + put_25d_iv) / 2
            if avg_iv > 0.001:
                skew = (call_25d_iv - put_25d_iv) / avg_iv
            else:
                skew = 0.0
            skew_values[exp_days] = skew
        
        if len(atm_ivs) < 2:
            return None
        
        # Calculate term structure slope
        exp_days_sorted = sorted(atm_ivs.keys())
        short_exp = exp_days_sorted[0]
        long_exp = exp_days_sorted[-1]
        iv_slope = atm_ivs[long_exp] - atm_ivs[short_exp]
        
        # Calculate skew slope
        if len(skew_values) >= 2:
            skew_exp_sorted = sorted(skew_values.keys())
            skew_slope = skew_values[skew_exp_sorted[-1]] - skew_values[skew_exp_sorted[0]]
        else:
            skew_slope = 0.0
        
        # Combined signal
        iv_slope_signal = -iv_slope
        skew_slope_signal = skew_slope
        combined_signal = iv_slope_signal * 0.4 + skew_slope_signal * 0.6
        
        # Get skew values for reporting
        skew_30d = skew_values.get(30, 0)
        skew_75d = skew_values.get(75, 0)
        
        return {
            'ticker': ticker_str,
            'current_price': round(float(current_price), 2),
            'iv_slope': round(float(iv_slope), 4),
            'skew_30d': round(float(skew_30d), 4),
            'skew_75d': round(float(skew_75d), 4),
            'skew_slope': round(float(skew_slope), 4),
            'iv_slope_signal': round(float(iv_slope_signal), 4),
            'skew_slope_signal': round(float(skew_slope_signal), 4),
            'combined_signal': round(float(combined_signal), 4),
            'signal_strength': round(float(combined_signal / 0.02), 4),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str} (IV skew term): {e}")
        return None

if __name__ == "__main__":
    print(f"\n📊 IV Skew-Term Structure Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print("Signal: ATM IV slope + skew slope composite")
    print("IV slope > 0 → upward term structure (mean reversion)")
    print("Skew slope > 0 → skew becomes bearish (negative sentiment)")
    results = []
    for t in TICKERS:
        r = compute_iv_skew_term_signal(t)
        if r:
            results.append(r)
    if not results:
        print("No data collected.")
        exit(1)
    df = pd.DataFrame(results)
    df_display = df.sort_values('signal_strength', ascending=False)
    cols = ['ticker', 'current_price', 'iv_slope', 'skew_slope', 'signal_strength']
    print(df_display[cols].to_string(index=False))
    print()
    print("💡 Interpretation:")
    print("  High positive signal → upward IV term structure + bearish skew = mean reversion BUY")
    print("  High negative signal → downward IV term structure + bullish skew = mean reversion SELL")
    print()
    os.makedirs("data", exist_ok=True)
    path = "data/iv_skew_term_latest.csv"
    df.to_csv(path, index=False)
    print(f"✅ Saved to {path}")
