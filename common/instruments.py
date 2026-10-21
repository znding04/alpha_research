"""Tradable instruments for common/validation.py, with cost assumptions.

Costs are deliberately conservative retail-ish estimates, fixed before any test ran:
- SPY: 1 bp per unit traded (half-spread + slippage), no borrow fee.
- 30d constant-maturity VIX futures: 0.025 vol pts half-spread per unit traded.
- VIXY: 5 bp per unit traded + 3%/yr borrow on short exposure.
- Delta-hedged 30d ATM straddles: 3% of premium per round trip (≈1.5% half-spread
  on ETF/large-cap ATM straddles), 5-day non-overlapping holds.
"""

import os

import numpy as np
import pandas as pd

from common.hedged import hedged_straddle_returns
from common.universe import TICKERS
from common.validation import Instrument, Panel
from common.vix_futures import constant_maturity_returns, load_vx_contracts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "results", "cache")
STRADDLE_STEP = 5
STRADDLE_COST = 0.03

_cm = None


def vix_cm() -> pd.DataFrame:
    global _cm
    if _cm is None:
        _cm = constant_maturity_returns(load_vx_contracts(2009))
    return _cm


def spy(data) -> Instrument:
    px = data.prices["SPY"].dropna()
    return Instrument("SPY", px.pct_change().shift(-1).dropna(), lambda to: to * 1e-4,
                      static={"buy & hold (benchmark)": 1.0})


def vix_futures() -> Instrument:
    cm = vix_cm()
    return Instrument("30d VIX futures", cm["cm_ret"],
                      lambda to, p=cm["cm_price"]: to * 0.025 / p.reindex(to.index),
                      static={"always short (benchmark)": -1.0})


def vixy() -> Instrument:
    import yfinance as yf
    px = yf.download("VIXY", start="2011-01-01", auto_adjust=True, progress=False)["Close"].squeeze()
    px.index = pd.to_datetime(px.index).tz_localize(None)
    return Instrument("VIXY", px.pct_change().shift(-1).dropna(), lambda to: to * 5e-4, borrow=0.03,
                      static={"always short (benchmark)": -1.0})


def futures_basis(data) -> pd.Series:
    """30d CM VIX futures / spot VIX − 1: the known predictor of VIX futures returns."""
    cm = vix_cm()
    vix = data.spx_term["VIX"]
    return (cm["cm_price"] / (vix * 100) - 1).reindex(vix.index)


def hedged_straddles(data, tickers=None) -> Panel:
    """5-day delta-hedged 30d ATM straddle returns per name, flat IV from each name's CBOE index."""
    tickers = [t for t in (tickers or TICKERS) if t in data.iv.columns]
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"straddle_{STRADDLE_STEP}d_{data.prices.index[-1]:%Y%m%d}.csv")
    if os.path.exists(path):
        ret = pd.read_csv(path, index_col=0, parse_dates=True)
    else:
        cols = {}
        for t in tickers:
            iv = data.iv[t].dropna()
            px = data.prices[t].reindex(iv.index).dropna()
            cols[t] = hedged_straddle_returns(px, lambda dt, m, iv=iv: np.full(len(m), iv.get(dt, np.nan)),
                                              STRADDLE_STEP)
        ret = pd.DataFrame(cols)
        ret.to_csv(path)
    # common non-overlapping rebalance calendar: every STRADDLE_STEP-th US trading day
    grid = data.prices["SPY"].dropna().index[::STRADDLE_STEP]
    ret = ret.reindex(grid).dropna(how="all")
    return Panel(f"delta-hedged straddles ({ret.shape[1]} names)", ret.clip(-1, 5), STRADDLE_STEP, STRADDLE_COST)
