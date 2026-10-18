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


# ---------------------------------------------------------------------------
# Forward returns (no look-ahead / no look-back)
# ---------------------------------------------------------------------------

def signal_as_of(path: str, date_cols=("date", "as_of", "timestamp")) -> pd.Timestamp:
    """Date a signal snapshot refers to.

    Uses the latest value of a date column in the CSV if one exists, otherwise
    the file's modification date. The forward-return base is the last close on
    or before this date, so a snapshot written at 2am Saturday is anchored to
    Friday's close.
    """
    try:
        df = pd.read_csv(path)
        for col in date_cols:
            if col in df.columns:
                dates = pd.to_datetime(df[col], errors="coerce").dropna()
                if len(dates):
                    return dates.max().normalize().tz_localize(None)
    except Exception:
        pass
    import os
    return pd.Timestamp(os.path.getmtime(path), unit="s").normalize()


def _daily_closes(ticker: str, start: pd.Timestamp) -> pd.Series:
    import yfinance as yf
    hist = yf.Ticker(ticker).history(start=start.strftime("%Y-%m-%d"), interval="1d")
    close = hist["Close"].dropna()
    close.index = pd.DatetimeIndex(close.index.date)
    return close


def forward_return(ticker: str, as_of, days: int = 5) -> float:
    """Return from the close on/before `as_of` to the close `days` trading days later.

    Returns NaN if those future bars don't exist yet, so a fresh snapshot can
    never be scored against returns that happened before it.
    """
    as_of = pd.Timestamp(as_of).normalize()
    try:
        close = _daily_closes(ticker, as_of - pd.Timedelta(days=10))
    except Exception:
        return np.nan
    base = close[close.index <= as_of]
    future = close[close.index > as_of]
    if base.empty or len(future) < days:
        return np.nan
    return float(future.iloc[days - 1] / base.iloc[-1] - 1)


def forward_vol_change(ticker: str, as_of, days: int = 5, rv_window: int = 30) -> float:
    """Relative change from trailing RV (rv_window days up to `as_of`) to RV over the next `days` trading days.

    Returns NaN if the forward window isn't complete yet.
    """
    as_of = pd.Timestamp(as_of).normalize()
    try:
        close = _daily_closes(ticker, as_of - pd.Timedelta(days=rv_window * 2))
    except Exception:
        return np.nan
    log_ret = np.log(close / close.shift(1)).dropna()
    past = log_ret[log_ret.index <= as_of].iloc[-rv_window:]
    future = log_ret[log_ret.index > as_of]
    if len(past) < rv_window // 2 or len(future) < days:
        return np.nan
    curr_rv = past.std() * np.sqrt(252)
    fut_rv = future.iloc[:days].std() * np.sqrt(252)
    return float((fut_rv - curr_rv) / curr_rv) if curr_rv > 0 else np.nan


def forward_returns_available(returns: pd.Series, as_of, days: int = 5) -> bool:
    """Print a notice and return False when no forward returns exist yet for a snapshot."""
    if returns.notna().any():
        return True
    print(f"\n⏳ Forward returns not available yet (signal as of "
          f"{pd.Timestamp(as_of).date()}, need {days} trading days after it).")
    print("   Real IC needs daily snapshots pooled over time (compute_ic needs ≥10 observations).")
    return False
