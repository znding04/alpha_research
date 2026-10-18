#!/usr/bin/env python3
"""Vol-of-Vol (Volatility of Volatility) alpha signal.

Computes the realized volatility of ATM IV over time.
High vol-of-vol = unstable vol regime = regime transition risk.
Low vol-of-vol = stable vol regime = mean-reversion friendly.

Cross-sectionally: Tickers with rising vol-of-vol signal regime instability
→ potential for large moves (direction uncertain, magnitude predictable).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from common.universe import TICKERS

# Historical data file for building IV time series
DATA_PATH = "data/vol_of_vol_history.csv"


def compute_atm_iv(ticker_str, target_dte_range=(14, 60)):
    """Get ATM IV from nearest liquid expiration within target DTE range."""
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
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None, current_price

        target_exp, dte = valid_exps[0]
        target_str = target_exp.strftime("%Y-%m-%d")

        chain = tq.option_chain(target_str)
        calls = chain.calls
        puts = chain.puts

        # Filter liquid options
        calls = calls[
            (calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)
        ].copy()
        puts = puts[
            (puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)
        ].copy()

        if len(calls) < 5 or len(puts) < 5:
            return None, current_price

        # Find ATM strike - use most liquid strike near ATM
        all_options = pd.concat([calls, puts], ignore_index=True)

        moneyness_low = current_price * 0.95
        moneyness_high = current_price * 1.05
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low) &
            (all_options['strike'] <= moneyness_high)
        ].copy()

        if len(near_atm) == 0:
            return None, current_price

        near_atm = near_atm[
            (near_atm['volume'].fillna(0) > 10) | (near_atm['openInterest'].fillna(0) > 100)
        ].copy()
        near_atm = near_atm[
            (near_atm['impliedVolatility'].notna()) &
            (near_atm['impliedVolatility'] > 0.01)
        ].copy()

        if len(near_atm) == 0:
            return None, current_price

        # Weighted average IV by liquidity
        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = (near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq
        else:
            atm_iv = near_atm['impliedVolatility'].median()

        return atm_iv, current_price

    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return None, None


def update_iv_history():
    """Fetch current ATM IV for all tickers and append to history."""
    os.makedirs("data", exist_ok=True)

    # Load existing history
    if os.path.exists(DATA_PATH):
        hist_df = pd.read_csv(DATA_PATH, parse_dates=['date'])
    else:
        hist_df = pd.DataFrame(columns=['date'] + TICKERS)

    today = pd.Timestamp(datetime.now().date())

    # Check if we already have today's data
    if today in hist_df['date'].values:
        print(f"  📅 Today's data already exists ({today.date()})")
        return hist_df

    # Fetch current IV for all tickers
    new_row = {'date': today}
    for t in TICKERS:
        atm_iv, _ = compute_atm_iv(t)
        new_row[t] = atm_iv if atm_iv is not None else np.nan
        if atm_iv is not None:
            print(f"  {t}: ATM IV = {atm_iv:.4f}")
        else:
            print(f"  {t}: Failed to fetch")

    # Append new row
    hist_df = pd.concat([hist_df, pd.DataFrame([new_row])], ignore_index=True)
    hist_df = hist_df.sort_values('date').reset_index(drop=True)

    # Save
    hist_df.to_csv(DATA_PATH, index=False)
    print(f"  ✅ Updated history: {len(hist_df)} days, saved to {DATA_PATH}")

    return hist_df


def compute_vol_of_vol(hist_df, window=20, min_periods=10):
    """Compute vol-of-vol (rolling std of daily IV changes) for each ticker."""
    # Daily IV returns (log changes)
    iv_returns = hist_df.set_index('date')[TICKERS].pct_change().dropna(how='all')

    # Rolling std of IV returns (annualized)
    vol_of_vol = iv_returns.rolling(window=window, min_periods=min_periods).std() * np.sqrt(252)

    return vol_of_vol


def compute_vol_of_vol_metrics(hist_df, window=20):
    """Compute vol-of-vol metrics for latest date."""
    vol_of_vol_df = compute_vol_of_vol(hist_df, window=window)

    if len(vol_of_vol_df) == 0:
        return []

    latest = vol_of_vol_df.iloc[-1]
    prev = vol_of_vol_df.iloc[-2] if len(vol_of_vol_df) > 1 else None

    results = []
    for t in TICKERS:
        vov = latest.get(t, np.nan)
        vov_prev = prev.get(t, np.nan) if prev is not None else np.nan

        if pd.isna(vov):
            continue

        # Also compute IV level and IV change
        iv_level = hist_df.set_index('date')[t].iloc[-1]
        iv_change = hist_df.set_index('date')[t].pct_change().iloc[-1]

        # Signal: rising vol-of-vol = regime instability
        vov_change = vov - vov_prev if pd.notna(vov_prev) else np.nan

        results.append({
            'ticker': t,
            'atm_iv': round(iv_level, 4) if pd.notna(iv_level) else np.nan,
            'iv_change_1d': round(iv_change, 4) if pd.notna(iv_change) else np.nan,
            'vol_of_vol': round(vov, 4),
            'vol_of_vol_change': round(vov_change, 4) if pd.notna(vov_change) else np.nan,
            'vov_percentile': None,  # Will compute after
        })

    # Add cross-sectional percentile of vol-of-vol
    vov_values = [r['vol_of_vol'] for r in results]
    for r in results:
        r['vov_percentile'] = round(
            pd.Series(vov_values).rank(pct=True)[vov_values.index(r['vol_of_vol'])], 4
        )

    return results


if __name__ == "__main__":
    print(f"\n📊 Vol-of-Vol Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Update history with today's IV
    print("\n📥 Fetching current ATM IV...")
    hist_df = update_iv_history()

    # Compute vol-of-vol metrics
    print("\n📈 Computing Vol-of-Vol (20-day window)...")
    results = compute_vol_of_vol_metrics(hist_df, window=20)

    if not results:
        print("No valid data.")
        exit(1)

    # Print summary
    for r in results:
        vov_signal = "🔥" if r['vol_of_vol'] > 0.5 else "⚡" if r['vol_of_vol'] > 0.3 else "📊"
        trend = "📈" if r['vol_of_vol_change'] > 0.05 else "📉" if r['vol_of_vol_change'] < -0.05 else "➡️"

        print(f"\n{r['ticker']}:")
        print(f"  ATM IV:            {r['atm_iv']:.4f} (1d chg: {r['iv_change_1d']:.4f})")
        print(f"  Vol-of-Vol (20d):  {r['vol_of_vol']:.4f} {vov_signal}")
        print(f"  VoV Change:        {r['vol_of_vol_change']:.4f} {trend}")
        print(f"  Cross-sec Pctile:  {r['vov_percentile']:.2f}")

    # Save latest snapshot
    os.makedirs("data", exist_ok=True)
    path = "data/vol_of_vol_latest.csv"
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")

    # Interpretation
    print("\n💡 Interpretation:")
    print("   Vol-of-Vol = rolling std of daily IV changes (annualized)")
    print("   High VoV (>0.5) → Unstable vol regime, regime transition risk")
    print("   Rising VoV → Increasing uncertainty, potential large moves")
    print("   Low VoV (<0.2) → Stable vol regime, mean-reversion friendly")
    print("   Cross-sec percentile: Rank vs peers (1.0 = highest instability)")

    print(f"\n   Total cost: ~$0.10-0.30 per run\n")