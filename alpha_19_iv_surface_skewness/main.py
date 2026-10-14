#!/usr/bin/env python3
"""IV Surface Skewness alpha signal.

Measures the third moment (skewness) of the IV smile across strikes.
Signal = smile skewness as proxy for risk-neutral skewness / tail risk expectations.
Positive skew = right-tail risk (call wing premium), negative = left-tail risk (put wing premium).
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime


TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def compute_smile_skewness(ticker_str):
    """Compute IV smile skewness (third moment) for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)

        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            return None

        # Fetch option chains - take most liquid near-term expiration (7-45 DTE)
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 7 <= dte <= 45:  # Focus on near-term for skew signal
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None

        # Use the most liquid near-term expiration (typically the front month)
        target_exp, target_dte = valid_exps[0]
        target_str = target_exp.strftime("%Y-%m-%d")

        chain = tq.option_chain(target_str)
        calls = chain.calls.copy()
        puts = chain.puts.copy()

        # Fix dtypes: volume and openInterest are float64 with NaN
        for df in [calls, puts]:
            df['volume'] = df['volume'].fillna(0)
            df['openInterest'] = df['openInterest'].fillna(0)

        # Filter liquid options with valid IV
        calls = calls[
            ((calls['volume'] > 10) | (calls['openInterest'] > 100)) &
            (calls['impliedVolatility'].notna()) &
            (calls['impliedVolatility'] > 0.01) &
            (calls['impliedVolatility'] < 3.0) &
            (calls['lastPrice'] > 0)
        ].copy()

        puts = puts[
            ((puts['volume'] > 10) | (puts['openInterest'] > 100)) &
            (puts['impliedVolatility'].notna()) &
            (puts['impliedVolatility'] > 0.01) &
            (puts['impliedVolatility'] < 3.0) &
            (puts['lastPrice'] > 0)
        ].copy()

        if len(calls) < 5 or len(puts) < 5:
            return None

        # Combine and sort by strike
        df = pd.concat([puts, calls], ignore_index=True)
        df = df.sort_values('strike').reset_index(drop=True)

        # Need sufficient strikes for moment calculation
        if len(df) < 10:
            return None

        # Compute moneyness (strike/spot)
        df['moneyness'] = df['strike'] / current_price

        # Focus on reasonable moneyness range (0.80 to 1.20)
        df = df[(df['moneyness'] >= 0.80) & (df['moneyness'] <= 1.20)].copy()

        if len(df) < 8:
            return None

        # Compute weighted moments using OI as weight (more robust than volume)
        weights = df['openInterest'].values
        if weights.sum() == 0:
            weights = df['volume'].values
        if weights.sum() == 0:
            weights = np.ones(len(df))

        weights = weights / weights.sum()
        iv = df['impliedVolatility'].values
        moneyness = df['moneyness'].values

        # Central moments of IV distribution across moneyness
        # We weight by OI to emphasize where market participants are positioned
        mean_iv = np.average(iv, weights=weights)
        centered_iv = iv - mean_iv

        # Variance (2nd moment) - IV dispersion
        var_iv = np.average(centered_iv**2, weights=weights)

        # Skewness (3rd moment) - IV smile asymmetry
        if var_iv > 0:
            skew_iv = np.average(centered_iv**3, weights=weights) / (var_iv**1.5)
        else:
            skew_iv = 0.0

        # Kurtosis (4th moment) - IV smile fat tails
        if var_iv > 0:
            kurt_iv = np.average(centered_iv**4, weights=weights) / (var_iv**2) - 3.0  # excess kurtosis
        else:
            kurt_iv = 0.0

        # Also compute risk-neutral skewness proxy via put/call wing IV difference
        # Left wing (OTM puts, moneyness < 0.95) vs Right wing (OTM calls, moneyness > 1.05)
        left_wing = df[df['moneyness'] < 0.95]
        right_wing = df[df['moneyness'] > 1.05]

        left_iv = left_wing['impliedVolatility'].mean() if len(left_wing) > 0 else np.nan
        right_iv = right_wing['impliedVolatility'].mean() if len(right_wing) > 0 else np.nan

        wing_skew = left_iv - right_iv if (pd.notna(left_iv) and pd.notna(right_iv)) else np.nan

        # ATM IV for reference
        atm_mask = (df['moneyness'] >= 0.98) & (df['moneyness'] <= 1.02)
        atm_iv = df.loc[atm_mask, 'impliedVolatility'].median() if atm_mask.any() else np.nan

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'expiration': target_str,
            'dte': target_dte,
            'iv_skewness': round(skew_iv, 6),
            'iv_kurtosis': round(kurt_iv, 6),
            'iv_variance': round(var_iv, 6),
            'wing_skew': round(wing_skew, 6) if pd.notna(wing_skew) else np.nan,
            'left_wing_iv': round(left_iv, 6) if pd.notna(left_iv) else np.nan,
            'right_wing_iv': round(right_iv, 6) if pd.notna(right_iv) else np.nan,
            'atm_iv': round(atm_iv, 4) if pd.notna(atm_iv) else np.nan,
            'n_strikes': len(df),
            'n_puts': len(puts),
            'n_calls': len(calls),
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📐 IV Surface Skewness Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_smile_skewness(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}) — {r['expiration']} ({r['dte']} DTE):")
        print(f"  IV Skewness (3rd moment):  {r['iv_skewness']:.6f}")
        print(f"  IV Kurtosis (excess):      {r['iv_kurtosis']:.6f}")
        print(f"  IV Variance:               {r['iv_variance']:.6f}")
        print(f"  Wing Skew (L-R):           {r['wing_skew']:.6f}" if pd.notna(r['wing_skew']) else f"  Wing Skew (L-R):           N/A")
        print(f"  Left Wing IV (OTM puts):   {r['left_wing_iv']:.6f}" if pd.notna(r['left_wing_iv']) else f"  Left Wing IV (OTM puts):   N/A")
        print(f"  Right Wing IV (OTM calls): {r['right_wing_iv']:.6f}" if pd.notna(r['right_wing_iv']) else f"  Right Wing IV (OTM calls): N/A")
        print(f"  ATM IV:                    {r['atm_iv']:.4f}" if pd.notna(r['atm_iv']) else f"  ATM IV:                    N/A")
        print(f"  Strikes: {r['n_strikes']} (P:{r['n_puts']} C:{r['n_calls']})")

    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_skewness_latest.csv"
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")