#!/usr/bin/env python3
"""IC Analysis for Vol-of-Vol signal.

Tests whether vol-of-vol metrics predict forward returns or vol regime changes.
"""

import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import sys
sys.path.insert(0, "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from common.utils import compute_ic, compute_signal_metrics, rolling_ic


TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_forward_returns(ticker_str, days_ahead=5):
    """Get forward returns for a ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{days_ahead + 10}d")
        if len(hist) < days_ahead + 1:
            return np.nan
        current = hist['Close'].iloc[-days_ahead - 1]
        future = hist['Close'].iloc[-1]
        return (future - current) / current
    except Exception:
        return np.nan


def get_forward_vol_change(ticker_str, days_ahead=5):
    """Get forward realized vol change for a ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        # Need extra days for the realized vol window
        hist = tq.history(period=f"{days_ahead + 30}d")
        if len(hist) < days_ahead + 10:
            return np.nan

        close = hist['Close']
        log_returns = np.log(close / close.shift(1)).dropna()

        # Current RV (last 30 days before forecast period)
        current_rv = log_returns.iloc[-days_ahead - 30:-days_ahead].std() * np.sqrt(252)
        # Forward RV (last 30 days including forecast period)
        future_rv = log_returns.iloc[-30:].std() * np.sqrt(252)

        if pd.isna(current_rv) or pd.isna(future_rv) or current_rv <= 0:
            return np.nan

        return (future_rv - current_rv) / current_rv
    except Exception:
        return np.nan


def run_ic_analysis():
    """Run IC analysis on current Vol-of-Vol signals vs forward returns/vol."""
    print(f"\n📈 IC Analysis — Vol-of-Vol — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Load latest vol-of-vol data
    vov_path = "data/vol_of_vol_latest.csv"
    if not os.path.exists(vov_path):
        print(f"❌ No VoV data found at {vov_path}. Run main.py first.")
        return

    vov_df = pd.read_csv(vov_path)

    # Get vol-of-vol signal per ticker
    vov_signal = vov_df.set_index('ticker')['vol_of_vol']
    vov_change_signal = vov_df.set_index('ticker')['vol_of_vol_change']
    vov_pctile_signal = vov_df.set_index('ticker')['vov_percentile']

    print("\nVol-of-Vol by ticker:")
    print(vov_signal.to_string())
    print("\nVoV Change by ticker:")
    print(vov_change_signal.to_string())
    print("\nVoV Percentile by ticker:")
    print(vov_pctile_signal.to_string())

    # Get forward returns (5-day)
    print("\nFetching 5-day forward returns...")
    forward_returns = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5)
        forward_returns[t] = ret
        print(f"  {t}: {ret:.4f}" if pd.notna(ret) else f"  {t}: N/A")

    # Get forward vol change (5-day)
    print("\nFetching 5-day forward vol change...")
    forward_vol_change = {}
    for t in TICKERS:
        vol_chg = get_forward_vol_change(t, 5)
        forward_vol_change[t] = vol_chg
        print(f"  {t}: {vol_chg:.4f}" if pd.notna(vol_chg) else f"  {t}: N/A")

    # Align and compute IC for returns
    signals = vov_signal
    returns = pd.Series(forward_returns)

    common = signals.index.intersection(returns.index)
    signals = signals.loc[common]
    returns = returns.loc[common]

    valid = signals.notna() & returns.notna()
    signals = signals[valid]
    returns = returns[valid]

    if len(signals) >= 3:
        ic = compute_ic(signals, returns)
        print(f"\n📊 IC (VoV level → 5-day returns): {ic:.4f}")

        # VoV change signal
        sig2 = vov_change_signal.loc[common]
        valid2 = sig2.notna() & returns.notna()
        if len(sig2[valid2]) >= 3:
            ic2 = compute_ic(sig2[valid2], returns[valid2])
            print(f"   VoV Change IC: {ic2:.4f}")

        # VoV percentile signal
        sig3 = vov_pctile_signal.loc[common]
        valid3 = sig3.notna() & returns.notna()
        if len(sig3[valid3]) >= 3:
            ic3 = compute_ic(sig3[valid3], returns[valid3])
            print(f"   VoV Percentile IC: {ic3:.4f}")
    else:
        print("\n⚠️ Insufficient data for returns IC (need ≥3 tickers)")

    # IC for vol regime change prediction
    print("\n📊 IC (VoV level → 5-day vol change):")
    vol_signals = vov_signal
    vol_returns = pd.Series(forward_vol_change)

    common_v = vol_signals.index.intersection(vol_returns.index)
    vol_signals = vol_signals.loc[common_v]
    vol_returns = vol_returns.loc[common_v]

    valid_v = vol_signals.notna() & vol_returns.notna()
    vol_signals = vol_signals[valid_v]
    vol_returns = vol_returns[valid_v]

    if len(vol_signals) >= 3:
        ic_vol = compute_ic(vol_signals, vol_returns)
        print(f"   VoV level → Vol change IC: {ic_vol:.4f}")

        sig2 = vov_change_signal.loc[common_v]
        valid2 = sig2.notna() & vol_returns.notna()
        if len(sig2[valid2]) >= 3:
            ic2_vol = compute_ic(sig2[valid2], vol_returns[valid2])
            print(f"   VoV change → Vol change IC: {ic2_vol:.4f}")

        sig3 = vov_pctile_signal.loc[common_v]
        valid3 = sig3.notna() & vol_returns.notna()
        if len(sig3[valid3]) >= 3:
            ic3_vol = compute_ic(sig3[valid3], vol_returns[valid3])
            print(f"   VoV percentile → Vol change IC: {ic3_vol:.4f}")
    else:
        print("   Insufficient data for vol change IC")

    print("\nNote: Full rolling IC requires historical VoV snapshots.")
    print("      Run main.py daily to build time series, then analyze.")

    return ic if 'ic' in locals() else None


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic historical data for demonstration."""
    print("\n🔄 Simulated Rolling IC (demo with random walks):")
    print("-" * 50)

    np.random.seed(42)
    n_days = 60

    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}
    vol_returns_data = {}

    for t in TICKERS:
        # Signal: Vol-of-vol (mean-reverting around 0.3)
        signal = 0.3 + np.cumsum(np.random.randn(n_days) * 0.02) + 0.05 * np.sin(np.arange(n_days) * 0.15)
        signal = np.clip(signal, 0.05, 0.8)
        signals_data[t] = signal

        # Returns: negative correlation with VoV (high VoV = risk-off = lower returns)
        returns_data[t] = -signal * 0.5 + np.random.randn(n_days) * 0.015

        # Vol change: positive correlation with VoV (high VoV predicts rising vol)
        vol_returns_data[t] = signal * 0.6 + np.random.randn(n_days) * 0.01

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    vol_returns_df = pd.DataFrame(vol_returns_data, index=dates).T

    signals_df.columns = dates
    returns_df.columns = dates
    vol_returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS
    vol_returns_df.index = TICKERS

    # Rolling IC for returns
    ric_ret = rolling_ic(signals_df, returns_df, window=20)
    metrics_ret = compute_signal_metrics(ric_ret)

    print(f"\nRolling IC (VoV → Returns, 20-day window, simulated):")
    for k, v in metrics_ret.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    # Rolling IC for vol change
    ric_vol = rolling_ic(signals_df, vol_returns_df, window=20)
    metrics_vol = compute_signal_metrics(ric_vol)

    print(f"\nRolling IC (VoV → Vol Change, 20-day window, simulated):")
    for k, v in metrics_vol.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric_ret, metrics_ret, ric_vol, metrics_vol


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()