"""Delta-hedged option P&L targets for historical IC (vol P&L with price exposure removed).

Two targets, both aligned to signal date t with the same 1-day execution lag as
common/ic_engine.py (position opened at close t+1):

1. variance_swap_pnl: realized variance over the next h trading days minus the
   30d implied variance at t+1 (VIX² is by construction the fair 30d SPX
   variance-swap strike). Model-free; what a daily delta-hedged option book earns
   in the limit.

2. hedged_straddle_returns: buy a 30-calendar-day ATM straddle at close t+1,
   delta-hedge daily at Black-Scholes delta, mark to model each day using the IV
   for the option's remaining maturity, exit after h trading days.
   Return = (straddle P&L + hedge P&L) / initial straddle premium.
   Simplifications: r = q = 0, close-to-close hedging, no transaction costs,
   options marked at the 30d-index-derived IV (no smile).
"""

import math

import numpy as np
import pandas as pd

from common.universe import SPX_TERM

OPTION_DAYS = 30  # calendar-day maturity of the straddle at inception
_erf = np.vectorize(math.erf)


def _ncdf(x):
    return 0.5 * (1 + _erf(x / math.sqrt(2)))


def _straddle(S, K, T, vol):
    """Black-Scholes ATM-ish straddle value and delta (r = q = 0)."""
    T = np.maximum(T, 1e-8)
    sd = vol * np.sqrt(T)
    d1 = (np.log(S / K) + 0.5 * sd ** 2) / sd
    d2 = d1 - sd
    call = S * _ncdf(d1) - K * _ncdf(d2)
    put = call - S + K
    delta = 2 * _ncdf(d1) - 1
    return call + put, delta


def spx_iv_at(term: pd.DataFrame, days: np.ndarray, date) -> np.ndarray:
    """IV for maturities `days` on `date`, linear in total variance across VIX9D/VIX/VIX3M/VIX6M."""
    row = term.loc[date]
    mats = np.array([SPX_TERM[c] for c in term.columns if pd.notna(row[c])], dtype=float)
    vols = np.array([row[c] for c in term.columns if pd.notna(row[c])], dtype=float)
    if len(mats) == 0:
        return np.full_like(days, np.nan, dtype=float)
    order = np.argsort(mats)
    mats, vols = mats[order], vols[order]
    tv = np.interp(days, mats, vols ** 2 * mats)  # flat extrapolation in total variance per day
    days = np.maximum(days, 1)
    # below the shortest point, keep the shortest vol (avoid exploding vol near expiry)
    tv = np.where(days < mats[0], vols[0] ** 2 * days, tv)
    return np.sqrt(tv / days)


def variance_swap_pnl(prices: pd.Series, iv: pd.Series, h: int = 21, lag: int = 1) -> pd.Series:
    """RV²(t+lag → t+lag+h, annualized) − IV²(t+lag), aligned to t."""
    r = np.log(prices / prices.shift(1))
    fwd_rv2 = (r ** 2).rolling(h).sum().shift(-(lag + h)) * 252 / h
    return fwd_rv2 - iv.shift(-lag) ** 2


def hedged_straddle_returns(prices: pd.Series, iv_fn, h: int, lag: int = 1, step: int = 1) -> pd.Series:
    """Delta-hedged 30d ATM straddle return over h trading days, aligned to signal date t.

    iv_fn(date, days_array) -> IV for those remaining maturities on that date.
    step: compute only every step-th signal date (step = h gives non-overlapping periods).
    """
    px = prices.dropna()
    dates = px.index
    S = px.values
    out = {}
    for i in range(0, len(dates) - lag - h, step):
        i0 = i + lag
        d0 = dates[i0]
        K = S[i0]
        path = slice(i0, i0 + h + 1)
        cal = np.array([(d - d0).days for d in dates[path]], dtype=float)
        rem = np.maximum(OPTION_DAYS - cal, 0)  # past expiry → settles at intrinsic
        vols = np.array([iv_fn(d, np.array([m]))[0] for d, m in zip(dates[path], rem)])
        if np.isnan(vols).any():
            continue
        V, delta = _straddle(S[path], K, rem / 365, vols)
        hedge = -(delta[:-1] * np.diff(S[path])).sum()
        out[dates[i]] = (V[-1] - V[0] + hedge) / V[0]
    return pd.Series(out)
