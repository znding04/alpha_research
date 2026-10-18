#!/usr/bin/env python3
"""IC Analysis for Gamma Exposure (GEX) signal.

Tests whether GEX metrics predict forward returns and volatility changes.
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
from common.utils import compute_ic, compute_signal_metrics, rolling_ic, forward_return, forward_vol_change, forward_returns_available, signal_as_of


from common.universe import TICKERS


def get_forward_returns(ticker_str, days_ahead=5, as_of=None):
    """Return over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_return(ticker_str, as_of, days_ahead)


def get_forward_vol_change(ticker_str, days_ahead=5, as_of=None):
    """Realized-vol change over the `days_ahead` trading days AFTER the signal snapshot date (NaN if not yet available)."""
    return forward_vol_change(ticker_str, as_of, days_ahead)


def run_ic_analysis():
    """Run IC analysis on current GEX signals vs forward returns."""
    print(f"\n📈 IC Analysis — Gamma Exposure (GEX) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    # Load latest GEX data
    gex_path = "data/gamma_exposure_latest.csv"
    if not os.path.exists(gex_path):
        print(f"❌ No GEX data found at {gex_path}. Run main.py first.")
        return

    gex_df = pd.read_csv(gex_path)
    as_of = signal_as_of(gex_path)

    # Get unique ticker-level metrics (from first row per ticker)
    ticker_metrics = gex_df.drop_duplicates(subset='ticker').set_index('ticker')

    print("\nGEX Metrics by Ticker:")
    for t in TICKERS:
        if t in ticker_metrics.index:
            row = ticker_metrics.loc[t]
            print(f"  {t}: Total GEX={row['total_gex']:,.0f}, Flip=${row['flip_strike']:.0f}, Dist={row['distance_to_flip_pct']:+.2f}%")

    # Get forward returns (5-day)
    print(f"\nFetching 5-day forward returns after {as_of.date()}...")
    forward_returns = {}
    forward_vol_chg = {}
    for t in TICKERS:
        ret = get_forward_returns(t, 5, as_of)
        vol_chg = get_forward_vol_change(t, 5, as_of)
        forward_returns[t] = ret
        forward_vol_chg[t] = vol_chg
        print(f"  {t}: Return={ret:.4f}, VolChg={vol_chg:.4f}" if pd.notna(ret) else f"  {t}: Return=N/A, VolChg=N/A")

    # Test signals
    signals_to_test = {
        'Total GEX': ticker_metrics['total_gex'],
        'Distance to Flip (%)': ticker_metrics['distance_to_flip_pct'],
    }
    if 'atm_gex' in ticker_metrics.columns:  # not written by every main.py version
        signals_to_test['ATM GEX'] = ticker_metrics['atm_gex']

    returns = pd.Series(forward_returns)
    if not forward_returns_available(returns, as_of, 5):
        return None

    vol_changes = pd.Series(forward_vol_chg)

    for name, signal in signals_to_test.items():
        common = signal.index.intersection(returns.index)
        sig = signal.loc[common]
        ret = returns.loc[common]

        valid = sig.notna() & ret.notna()
        sig = sig[valid]
        ret = ret[valid]

        if len(sig) >= 3:
            ic = compute_ic(sig, ret)
            print(f"\n  {name} vs 5-day Return IC: {ic:.4f}")

            # Also test vs vol change
            vol_common = sig.index.intersection(vol_changes.index)
            sig_v = sig.loc[vol_common]
            vol = vol_changes.loc[vol_common]
            valid_v = sig_v.notna() & vol.notna()
            if len(sig_v[valid_v]) >= 3:
                ic_v = compute_ic(sig_v[valid_v], vol[valid_v])
                print(f"  {name} vs 5-day Vol Change IC: {ic_v:.4f}")
        else:
            print(f"\n  {name}: Insufficient data ({len(sig)} tickers)")

    print("\nNote: Full rolling IC requires historical GEX snapshots.")
    print("      Run main.py daily to build time series, then analyze.")


def simulate_rolling_ic():
    """Simulate rolling IC with synthetic historical data for demonstration."""
    print("\n🔄 SYNTHETIC — not evidence. Simulated Rolling IC (demo with synthetic data):")
    print("-" * 50)

    np.random.seed(42)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    signals_data = {}
    returns_data = {}
    vol_data = {}

    for t in TICKERS:
        # GEX signal: mean-reverting around zero, negative = short gamma = higher vol
        base_gex = np.random.randn() * 5000  # random starting GEX
        signal = base_gex + np.cumsum(np.random.randn(n_days) * 500)
        signals_data[t] = signal

        # Returns: negative GEX (short gamma) → higher realized vol → negative returns in stress
        # Positive GEX (long gamma) → vol suppression → slight positive drift
        returns_data[t] = -signal * 0.00001 + np.random.randn(n_days) * 0.012

        # Vol change: short gamma amplifies moves → vol increases
        vol_data[t] = -signal * 0.00002 + np.random.randn(n_days) * 0.05

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    vol_df = pd.DataFrame(vol_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    vol_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS
    vol_df.index = TICKERS

    # Rolling IC vs returns
    ric_ret = rolling_ic(signals_df, returns_df, window=20)
    metrics_ret = compute_signal_metrics(ric_ret)

    print(f"Rolling IC vs Returns (20-day window, simulated):")
    for k, v in metrics_ret.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    # Rolling IC vs vol change
    ric_vol = rolling_ic(signals_df, vol_df, window=20)
    metrics_vol = compute_signal_metrics(ric_vol)

    print(f"\nRolling IC vs Vol Change (20-day window, simulated):")
    for k, v in metrics_vol.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")

    return ric_ret, metrics_ret, ric_vol, metrics_vol


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()