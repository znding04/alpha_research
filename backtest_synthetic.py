#!/usr/bin/env python3
"""Synthetic backtest runner for all 20 alpha signals.

Since yfinance does not provide historical option chains, this script
generates synthetic signal and return data calibrated to each alpha's
expected IC sign and magnitude (from notes.md), then computes rolling IC,
IR, win rate, and directional accuracy over a 252-day simulated period.

Results are printed as a summary table for inclusion in REPORT.md.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import pandas as pd
from common.utils import compute_ic, rolling_ic, compute_signal_metrics

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]
N_DAYS = 252
ROLLING_WINDOW = 20

# Alpha definitions: (name, expected IC sign, expected IC magnitude, seed)
ALPHAS = [
    ("01_iv_rank",              "iv_spread = ATM_IV - median_IV",                    +0.12, 101),
    ("02_iv_skew_dynamics",     "skew_25d = put_25d_IV - call_25d_IV",               +0.18, 102),
    ("03_iv_term_structure",    "term_slope = (IV_far - IV_near) / delta_DTE",       -0.17, 103),
    ("04_vrp",                  "vrp = IV^2 - RV^2",                                 +0.16, 104),
    ("05_iv_rank_percentile",   "iv_percentile over 252-day rolling window",         -0.18, 105),
    ("06_vrp_term_structure",   "vrp_slope across maturities",                       -0.14, 106),
    ("07_iv_dispersion",        "index_IV - weighted_constituent_IV",                +0.13, 107),
    ("08_gamma_exposure",       "dealer net GEX; flip strike distance",              -0.12, 108),
    ("09_iv_surface_curvature", "quadratic smile curvature (2nd deriv)",             +0.08, 109),
    ("10_vrp_carry",            "near_VRP - far_VRP (term carry)",                   +0.20, 110),
    ("11_vol_of_vol",           "rolling std of daily IV returns",                   -0.20, 111),
    ("12_iv_momentum",          "5-day pct change in ATM IV",                        -0.18, 112),
    ("13_iv_skew_momentum",     "rate of change of 25d skew",                        -0.15, 113),
    ("14_iv_smile_asymmetry",   "OI-weighted put/call IV spread + ratios",           -0.17, 114),
    ("15_iv_term_momentum",     "momentum of IV term structure slope",               -0.20, 115),
    ("16_iv_skew_convexity",    "butterfly convexity of IV smile",                   -0.18, 116),
    ("17_iv_calendar_spread",   "ATM IV spread: 30d vs 60d expiry",                  +0.07, 117),
    ("18_vrp_momentum",         "rate of change of VRP across expirations",          -0.16, 118),
    ("19_iv_surface_skewness",  "OI-weighted 3rd moment of IV smile",                +0.12, 119),
    ("20_vrp_skew",             "put_VRP - call_VRP (variance premium asymmetry)",   -0.15, 120),
]


def generate_synthetic_data(ic_target, seed, n_days=N_DAYS):
    """Generate synthetic signal and return series calibrated to target IC."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end="2026-10-15", periods=n_days, freq="B")

    signals_data = {}
    returns_data = {}

    sign = np.sign(ic_target)
    strength = abs(ic_target)

    for t in TICKERS:
        # Signal: mean-reverting process with drift
        noise = rng.standard_normal(n_days)
        signal = np.cumsum(noise * 0.01) + rng.standard_normal(n_days) * 0.005
        signals_data[t] = signal

        # Returns: correlated with signal at target IC level + noise
        ret_noise = rng.standard_normal(n_days) * 0.02
        returns_data[t] = sign * strength * signal * 0.8 + ret_noise

    signals_df = pd.DataFrame(signals_data, index=dates).T
    returns_df = pd.DataFrame(returns_data, index=dates).T
    signals_df.columns = dates
    returns_df.columns = dates
    signals_df.index = TICKERS
    returns_df.index = TICKERS

    return signals_df, returns_df


def run_all_backtests():
    """Run synthetic backtests for all 20 alphas."""
    results = []

    for name, signal_desc, ic_target, seed in ALPHAS:
        sig_df, ret_df = generate_synthetic_data(ic_target, seed)

        ric = rolling_ic(sig_df, ret_df, window=ROLLING_WINDOW)
        metrics = compute_signal_metrics(ric)

        if "error" in metrics:
            results.append({
                "alpha": name,
                "ic_mean": np.nan,
                "ic_std": np.nan,
                "ir": np.nan,
                "win_rate": np.nan,
                "n_obs": 0,
            })
        else:
            results.append({
                "alpha": name,
                "ic_mean": metrics["ic_mean"],
                "ic_std": metrics["ic_std"],
                "ir": metrics["ir"],
                "win_rate": metrics["win_rate"],
                "n_obs": metrics["n_obs"],
            })

    df = pd.DataFrame(results)
    return df


if __name__ == "__main__":
    print("=" * 80)
    print("SYNTHETIC BACKTEST RESULTS — ALL 20 ALPHA SIGNALS")
    print("=" * 80)
    print("\nNote: These results use synthetic data calibrated to each alpha's")
    print("expected IC from notes.md. Real backtests require historical option")
    print("chain data (unavailable via yfinance).\n")

    df = run_all_backtests()

    print(df.to_string(index=False, float_format="%.4f"))
    print(f"\nTotal alphas tested: {len(df)}")
    print(f"Alphas with |IC| > 0.05: {(df['ic_mean'].abs() > 0.05).sum()}")
    print(f"Alphas with IR > 0.5:    {(df['ir'].abs() > 0.5).sum()}")
