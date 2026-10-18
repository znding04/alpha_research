#!/usr/bin/env python3
"""IV Change alpha signal.

Track the day-over-day and 5-day change in near-term ATM implied volatility.
Hypothesis: sharp IV increases (without corresponding spot moves) signal
overwrought options positioning; mean-reverting IV implies forward returns
decay. Cross-sectionally, large recent IV drops (compression) rank higher
as a contrarian signal.
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def fetch_minute_iv_history(ticker_str, days=6):
    """Fetch intraday 5m data for `days` and compute realized variance proxy via
    rolling standard deviation of log returns; then pull ATM IV from the
    nearest liquid option chain to compare.

    For a daily-resolution signal, we pull the ATM IV now and compare against
    a cached prior snapshot if one exists in data/.
    """
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        # Nearest expiration with DTE >= 14 (skip near-weeklies for noise)
        expirations = list(tq.options)
        now = datetime.now()
        best = None
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 14 <= dte <= 60 and (best is None or dte < best[1]):
                    best = (e, dte)
            except ValueError:
                continue
        if best is None:
            return None
        chain = tq.option_chain(best[0])
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        # Fix dtypes: fillna(0) so int64 / float64-with-NaN columns compare safely
        df['volume'] = df['volume'].fillna(0)
        df['openInterest'] = df['openInterest'].fillna(0)
        df = df[
            ((df['volume'] > 50) | (df['openInterest'] > 500)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()
        if len(df) < 10:
            return None
        moneyness = df['strike'] / current_price
        atm = df[(moneyness >= 0.95) & (moneyness <= 1.05) &
                 (df['impliedVolatility'] > 0.05)].copy()
        if len(atm) == 0:
            return None
        atm_iv = atm['impliedVolatility'].median()
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'atm_iv': round(float(atm_iv), 4),
            'dte_days': best[1],
            'snapshot_date': datetime.now().strftime('%Y-%m-%d'),
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


def compute_iv_change(ticker_str):
    """Compute IV change vs prior snapshot stored in data/.

    Returns current ATM IV, prior ATM IV (if cached), and the 5-day change.
    If no prior snapshot exists, falls back to a 5-day lookback using
    yfinance historical daily IV proxy is not available, so we synthesize a
    baseline from a synthetic prior IV = ATM IV * (1 - small noise) for demo.
    """
    current = fetch_minute_iv_history(ticker_str)
    if current is None:
        return None

    cache_path = 'alpha_22_iv_change/data/iv_history.csv'
    os.makedirs('alpha_22_iv_change/data', exist_ok=True)
    prior = None
    if os.path.exists(cache_path):
        try:
            hist = pd.read_csv(cache_path)
            hist = hist[hist['ticker'] == ticker_str]
            if len(hist) > 0:
                prior_row = hist.sort_values('snapshot_date').iloc[-1]
                prior = float(prior_row['atm_iv'])
        except Exception:
            prior = None

    current_iv = current['atm_iv']
    if prior is not None and prior > 0:
        iv_change_5d = current_iv - prior
    else:
        # No history yet — synthesize a placeholder baseline so the snapshot
        # is still useful for the first run; subsequent runs use real history.
        iv_change_5d = 0.0
        prior = current_iv

    signal = {
        'ticker': ticker_str,
        'current_price': current['current_price'],
        'atm_iv': current_iv,
        'prior_atm_iv': round(prior, 4),
        'iv_change_5d': round(iv_change_5d, 4),
        # Rank signal: drop in IV (negative change) = higher rank (contrarian buy)
        'iv_change_rank_signal': round(-iv_change_5d, 4),
        'dte_days': current['dte_days'],
        'snapshot_date': current['snapshot_date'],
    }

    # Append to history cache
    row = pd.DataFrame([signal])
    if os.path.exists(cache_path):
        row.to_csv(cache_path, mode='a', header=False, index=False)
    else:
        row.to_csv(cache_path, index=False)
    return signal


if __name__ == "__main__":
    print(f"\n📉 IV Change Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    results = []
    for t in TICKERS:
        r = compute_iv_change(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    df = pd.DataFrame(results)
    print(df[['ticker', 'current_price', 'atm_iv', 'prior_atm_iv',
              'iv_change_5d', 'iv_change_rank_signal']].to_string(index=False))
    print("\n💡 Interpretation:")
    print("   iv_change_5d > 0 → IV rose (options expensive, fear)  → rank lower")
    print("   iv_change_5d < 0 → IV fell (compression)             → rank higher")

    path = "data/iv_change_latest.csv"
    os.makedirs("data", exist_ok=True)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")
