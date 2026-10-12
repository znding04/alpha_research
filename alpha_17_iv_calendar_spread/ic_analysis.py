#!/usr/bin/env python3
"""IC Analysis for IV Calendar Spread alpha signal.

Computes Information Coefficient (IC) and rolling IC to measure
predictive power of calendar spread for forward returns.
"""

import os
import sys
sys.path.insert(0, "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Import shared utilities
from common.utils import compute_ic, rolling_ic, compute_signal_metrics, half_life_of_mean_reversion

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_atm_iv(ticker_str, target_dte, max_dte=180):
    """Get ATM IV for a specific target DTE by finding closest available expiration."""
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
                if 0 < dte <= max_dte:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None, None

        exp_date, dte = min(valid_exps, key=lambda x: abs(x[1] - target_dte))
        exp_str = exp_date.strftime("%Y-%m-%d")

        chain = tq.option_chain(exp_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        df['volume'] = df['volume'].fillna(0)
        df['openInterest'] = df['openInterest'].fillna(0)
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()

        if len(df) < 10:
            return None, None

        atm_idx = (df['strike'] - current_price).abs().idxmin()
        atm_iv = df.loc[atm_idx, 'impliedVolatility']

        if pd.isna(atm_iv) or atm_iv <= 0:
            return None, None

        return atm_iv, dte

    except Exception:
        return None, None


def compute_historical_spreads(ticker_str, short_dte=30, long_dte=60, days_back=60):
    """Compute historical calendar spreads by simulating past observations.
    
    NOTE: This is a simplified approach - we use current option chains but
    for true historical analysis we'd need historical option data.
    For now, we compute the current spread and use it as a signal
    for the most recent period.
    """
    # This is a placeholder for historical backtesting
    # Real implementation would require historical option data
    pass


def compute_ic_analysis():
    """Run IC analysis on the calendar spread signal.
    
    Since we don't have historical option data, this demonstrates
    the framework. With historical data, we would:
    1. Load historical calendar spreads (signal)
    2. Load forward returns (e.g., 1-day, 5-day, 10-day)
    3. Compute cross-sectional IC for each date
    4. Compute rolling IC and signal metrics
    """
    print(f"\n📊 IV Calendar Spread IC Analysis — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    print("\n⚠️  NOTE: This is a framework demonstration.")
    print("   Historical option data required for true IC backtest.")
    print("   Current implementation computes live signal only.\n")

    # Compute current signals
    signals = {}
    for t in TICKERS:
        short_iv, short_dte = get_atm_iv(t, 30)
        long_iv, long_dte = get_atm_iv(t, 60)
        if short_iv is not None and long_iv is not None:
            spread = short_iv - long_iv
            signals[t] = spread
            print(f"  {t}: spread = {spread:.4f}")

    if not signals:
        print("No signals computed.")
        return

    # Placeholder: generate synthetic forward returns for demo
    # In production, replace with actual forward returns from price data
    np.random.seed(42)
    forward_returns = {t: np.random.normal(0, 0.01) for t in signals.keys()}

    # Compute IC
    signal_series = pd.Series(signals)
    return_series = pd.Series(forward_returns)

    ic = compute_ic(signal_series, return_series)
    print(f"\n📈 Current IC (vs synthetic returns): {ic:.4f}")

    # In production with historical data:
    # signals_df = load_historical_signals()  # (assets x dates)
    # returns_df = load_forward_returns()     # (assets x dates)
    # rolling_ic_series = rolling_ic(signals_df, returns_df, window=60)
    # metrics = compute_signal_metrics(rolling_ic_series)
    # half_life = half_life_of_mean_reversion(rolling_ic_series)

    print("\n📋 Framework ready for historical data integration:")
    print("   1. Add historical option data source")
    print("   2. Build signals_df (tickers x dates)")
    print("   3. Build returns_df (tickers x dates, forward-looking)")
    print("   4. Call rolling_ic(), compute_signal_metrics(), half_life_of_mean_reversion()")


if __name__ == "__main__":
    compute_ic_analysis()