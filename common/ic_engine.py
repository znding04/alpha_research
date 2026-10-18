"""Historical IC engine shared by every alpha_*/historical.py.

Conventions (identical for all alphas, so results are comparable):
- Signal value at date t uses data up to the close of t only.
- One-day execution lag: forward return from close t+1 to close t+1+h.
  (CBOE vol indices settle at 4:15pm, after the 4:00pm equity close, so a
  same-day close would leak ~15 minutes of information.)
- Targets: forward log return of the underlying, and forward log change of its
  30d IV (many hypotheses are about vol mean reversion, not price).
- Cross-sectional IC: Spearman across tickers each day (needs >= MIN_NAMES).
- Time-series IC: Spearman over time for each ticker; pooled = mean over tickers.
- t-stats: Newey-West with lag = h for daily (overlapping) IC series; for a
  time-series IC, t ~= IC * sqrt(N / h) (effective non-overlapping sample).
"""

import numpy as np
import pandas as pd

HORIZONS = (1, 5, 21)
MIN_NAMES = 8
LAG = 1
SPLIT_DATE = "2019-01-01"  # in-sample / out-of-sample stability check


def forward_log_change(level: pd.DataFrame, h: int, lag: int = LAG) -> pd.DataFrame:
    """log(X[t+lag+h] / X[t+lag]) aligned to date t."""
    return np.log(level.shift(-(lag + h)) / level.shift(-lag))


def _row_spearman(a: pd.DataFrame, b: pd.DataFrame, min_names: int) -> pd.Series:
    mask = a.notna() & b.notna()
    ra = a.where(mask).rank(axis=1)
    rb = b.where(mask).rank(axis=1)
    ra = ra.sub(ra.mean(axis=1), axis=0)
    rb = rb.sub(rb.mean(axis=1), axis=0)
    num = (ra * rb).sum(axis=1)
    den = np.sqrt((ra ** 2).sum(axis=1) * (rb ** 2).sum(axis=1))
    ic = num / den.replace(0, np.nan)
    return ic.where(mask.sum(axis=1) >= min_names).dropna()


def nw_tstat(x: pd.Series, lags: int) -> float:
    """Newey-West t-statistic for the mean of x."""
    x = x.dropna().values
    n = len(x)
    if n < 20:
        return np.nan
    e = x - x.mean()
    var = e @ e / n
    for k in range(1, min(lags, n - 1) + 1):
        w = 1 - k / (lags + 1)
        var += 2 * w * (e[k:] @ e[:-k]) / n
    return float(x.mean() / np.sqrt(var / n)) if var > 0 else np.nan


def cross_sectional_ic(signal: pd.DataFrame, target: pd.DataFrame, h: int) -> dict:
    ic = _row_spearman(signal, target.reindex_like(signal), MIN_NAMES)
    if len(ic) < 60:
        return {}
    pre, post = ic[ic.index < SPLIT_DATE], ic[ic.index >= SPLIT_DATE]
    return {
        "ic": ic.mean(),
        "t": nw_tstat(ic, h),
        "hit": (ic > 0).mean(),
        "n": len(ic),
        "ic_pre2019": pre.mean() if len(pre) else np.nan,
        "ic_post2019": post.mean() if len(post) else np.nan,
        "series": ic,
    }


def time_series_ic(signal: pd.DataFrame, target: pd.DataFrame, h: int) -> dict:
    per = {}
    for t in signal.columns:
        df = pd.concat([signal[t], target[t]], axis=1).dropna()
        if len(df) < 252:
            continue
        ic = df.iloc[:, 0].rank().corr(df.iloc[:, 1].rank())
        post = df[df.index >= SPLIT_DATE]
        per[t] = {
            "ic": ic,
            "t": ic * np.sqrt(len(df) / h),
            "n": len(df),
            "ic_post2019": post.iloc[:, 0].rank().corr(post.iloc[:, 1].rank()) if len(post) > 252 else np.nan,
        }
    if not per:
        return {}
    pooled = np.mean([v["ic"] for v in per.values()])
    # pooled t: average per-ticker t / sqrt(k) ignores cross-correlation, so report the mean t instead (conservative)
    return {"ic": pooled, "t": np.mean([v["t"] for v in per.values()]), "n_tickers": len(per), "per_ticker": per}


def evaluate(signal: pd.DataFrame, data, horizons=HORIZONS) -> dict:
    """Score a signal (date x ticker) against forward returns and forward IV changes."""
    signal = signal.replace([np.inf, -np.inf], np.nan)
    targets = {"ret": data.prices, "div": data.iv}
    out = {}
    for tname, level in targets.items():
        for h in horizons:
            fwd = forward_log_change(level.reindex(columns=signal.columns), h)
            key = f"{tname}_{h}d"
            out[key] = {
                "cs": cross_sectional_ic(signal, fwd, h) if signal.shape[1] >= MIN_NAMES else {},
                "ts": time_series_ic(signal, fwd, h),
            }
    return out
