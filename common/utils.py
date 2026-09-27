"""Shared utilities for alpha signal computation and analysis."""

from typing import Optional
import numpy as np
import pandas as pd


def compute_ic(signals: pd.Series, forward_returns: pd.Series) -> float:
    """Compute Information Coefficient (rank IC) between signal and forward returns.
    
    Args:
        signals: Cross-sectional signal values indexed by (asset, date).
        forward_returns: Forward returns for same assets/dates.
        
    Returns:
        Spearman rank correlation (IC).
    """
    if len(signals) < 10:
        return np.nan
    common_index = signals.index.intersection(forward_returns.index)
    s = signals.loc[common_index]
    r = forward_returns.loc[common_index]
    return s.rank().corr(r.rank())


def rolling_ic(
    signals_df: pd.DataFrame,
    returns_df: pd.DataFrame,
    window: int = 60,
    min_periods: Optional[int] = None,
) -> pd.Series:
    """Rolling Information Coefficient over time.
    
    Args:
        signals_df: DataFrame with assets as rows, dates as columns
        returns_df: DataFrame with assets as rows, dates as columns (forward returns)
        window: Rolling window size in days
        min_periods: Minimum observations per window
    
    Returns:
        Series of IC values indexed by date
    """
    results = []
    dates = sorted(signals_df.columns)
    min_p = min_periods or max(window // 3, 10)
    
    for i in range(len(dates) - window + 1):
        start_idx = i
        end_idx = i + window
        window_dates = dates[start_idx:end_idx]
        
        # Get signals and returns for this window
        window_signals = signals_df[window_dates]
        window_returns = returns_df[window_dates]
        
        # Stack to long format: (asset, date) -> value
        sig_stacked = window_signals.stack()
        ret_stacked = window_returns.stack()
        
        # Align on common index
        common_idx = sig_stacked.index.intersection(ret_stacked.index)
        if len(common_idx) < min_p:
            results.append((dates[end_idx - 1], np.nan))
            continue
        
        sig_aligned = sig_stacked.loc[common_idx]
        ret_aligned = ret_stacked.loc[common_idx]
        
        # Compute Spearman rank correlation
        ic = sig_aligned.rank().corr(ret_aligned.rank())
        results.append((dates[end_idx - 1], ic))
    
    return pd.Series(dict(results), name='rolling_ic')


def compute_signal_metrics(ic_series: pd.Series) -> dict:
    """Compute summary metrics for an IC time series."""
    clean = ic_series.dropna()
    if len(clean) < 5:
        return {"error": "insufficient data"}
    
    return {
        "ic_mean": float(clean.mean()),
        "ic_std": float(clean.std()),
        "ir": float(clean.mean() / clean.std()) if clean.std() > 0 else np.nan,
        "win_rate": float((clean > 0).mean()),
        "n_obs": int(len(clean)),
        "max_ic": float(clean.max()),
        "min_ic": float(clean.min()),
    }


def half_life_of_mean_reversion(data: pd.Series, max_lag: int = 20) -> float:
    """Estimate half-life of mean reversion via AR(1) regression."""
    if len(data) < max_lag + 10:
        return np.nan
    
    y = data.iloc[max_lag:]
    x = data.iloc[:-max_lag]
    
    # OLS: y_t = alpha + beta * x_{t-1} + epsilon
    n = len(y)
    x_mean = x.mean()
    y_mean = y.mean()
    
    numerator = ((x - x_mean) * (y - y_mean)).sum()
    denominator = ((x - x_mean) ** 2).sum()
    
    if denominator == 0:
        return np.nan
    
    beta = numerator / denominator
    half_life = -np.log(2) / np.log(beta) if abs(beta) < 1 and beta != 0 else np.inf
    
    return float(half_life)
