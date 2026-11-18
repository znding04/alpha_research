#!/usr/bin/env python3
"""IC Analysis for ATM IV term-structure convexity — alpha_45.

Tests whether curvature_norm (ATM butterfly across ~14/30/75d tenors) predicts
forward returns cross-sectionally. A single snapshot IC is descriptive only;
real IC needs daily snapshots accumulated over time (collect_snapshots.py).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime

from common.universe import TICKERS
from common.utils import (
    compute_ic, compute_signal_metrics, rolling_ic,
    forward_return, forward_vol_change,
    forward_returns_available, signal_as_of,
)

SIG_PATH = "data/iv_term_convexity_latest.csv"
FOCUS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def run_ic_analysis(days_ahead=5):
    """Run IC analysis on the current convexity signals vs forward returns."""
    print(f"\n📈 IC Analysis — IV Term-Structure Convexity — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 74)

    if not os.path.exists(SIG_PATH):
        print(f"❌ No signal data at {SIG_PATH}. Run main.py first.")
        return None

    df = pd.read_csv(SIG_PATH)
    as_of = signal_as_of(SIG_PATH)

    signal = df.set_index('ticker')['curvature_norm']
    print(f"\ncurvature_norm by ticker (as of {as_of.date()}):")
    print(signal.to_string())

    print(f"\nFetching {days_ahead}-day forward returns after {as_of.date()}...")
    fwd = {t: forward_return(t, as_of, days_ahead) for t in TICKERS}
    for t in TICKERS:
        print(f"  {t}: {fwd[t]:+.4f}" if pd.notna(fwd[t]) else f"  {t}: N/A")

    returns = pd.Series(fwd)
    if not forward_returns_available(returns, as_of, days_ahead):
        return None

    # --- Cross-sectional IC (all tickers with data) ---
    common = signal.index.intersection(returns.index)
    s = signal.loc[common]
    r = returns.loc[common]
    mask = s.notna() & r.notna()
    s, r = s[mask], r[mask]

    if len(s) < 3:
        print("\n⚠️ Insufficient tickers for cross-sectional IC (need ≥3).")
        return None

    ic = compute_ic(s, r)
    print(f"\n📊 Cross-sectional rank IC ({days_ahead}d fwd, n={len(s)}): {ic:.4f}")

    # Focus subset IC
    fs = s[s.index.isin(FOCUS)]
    fr = r[r.index.isin(FOCUS)]
    if len(fs) >= 3:
        ic_focus = compute_ic(fs, fr)
        print(f"   Focus-subset IC (n={len(fs)}): {ic_focus:.4f}")

    # Robustness: raw curvature (not normalized)
    if 'curvature' in df.columns:
        s_raw = df.set_index('ticker')['curvature'].reindex(common)
        m = s_raw.notna() & r.notna()
        if m.sum() >= 3:
            print(f"   Raw curvature IC (robustness): {compute_ic(s_raw[m], r[m]):.4f}")

    if ic > 0.05:
        print("   → Positive IC: richer mid-tenor belly predicts higher forward returns")
    elif ic < -0.05:
        print("   → Negative IC: richer mid-tenor belly predicts lower forward returns")
    else:
        print("   → Near-zero IC: no clear cross-sectional predictive power here")

    print("\nNote: single-snapshot IC is noise; real IC needs ≥60 daily snapshots.")

    # Secondary: does curvature predict forward vol change? (vol-prediction check)
    print(f"\nForward realized-vol change ({days_ahead}d) vs signal:")
    vol_chg = {}
    for t in TICKERS:
        vc = forward_vol_change(t, as_of, days_ahead)
        vol_chg[t] = vc
    vc_series = pd.Series(vol_chg)
    if vc_series.notna().sum() >= 3:
        vc_al = vc_series.reindex(s.index)
        m2 = s.notna() & vc_al.notna()
        if m2.sum() >= 3:
            ic_vol = compute_ic(s[m2], vc_al[m2])
            print(f"   IC vs forward ΔRV: {ic_vol:+.4f} (rich belly → vol should fall if crowded)")

    return ic


def simulate_rolling_ic():
    """Synthetic rolling-IC demo — NOT evidence of predictability."""
    print("\n🔄 SYNTHETIC — not evidence. Rolling IC demo (random walks):")
    print("-" * 50)
    np.random.seed(45)
    n_days = 60
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='B')

    sig_data, ret_data = {}, {}
    for t in TICKERS:
        s = 0.0004 + np.cumsum(np.random.randn(n_days) * 0.0001)
        sig_data[t] = s
        ret_data[t] = s * 0.5 + np.random.randn(n_days) * 0.012

    signals_df = pd.DataFrame(sig_data, index=dates).T
    returns_df = pd.DataFrame(ret_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    ric = rolling_ic(signals_df, returns_df, window=20)
    metrics = compute_signal_metrics(ric)
    print("Rolling IC (20-day window, simulated):")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}" if isinstance(v, float) else f"  {k}: {v}")
    return ric, metrics


if __name__ == "__main__":
    run_ic_analysis()
    simulate_rolling_ic()
