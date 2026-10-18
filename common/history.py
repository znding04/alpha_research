"""Historical data loader for time-series alpha research.

yfinance has no historical option chains, so historical signals are rebuilt
from CBOE implied-vol indices (free daily CSVs, ~2004/2011 onward):

- 30-day IV per underlying (VIX for SPY, VXN for QQQ, VXAPL for AAPL, ...)
- SPX IV term structure (VIX9D / VIX / VIX3M / VIX6M)
- VVIX, SKEW, implied correlation (COR1M / COR3M)

Underlying prices come from yfinance (split/dividend adjusted closes).
Everything is cached under data/history/ (gitignored); pass refresh=True to re-download.
"""

import io
import os
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from common.universe import HIST_TICKERS, SPX_EXTRA, SPX_TERM, VOL_INDEX

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(ROOT, "data", "history")
CBOE_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{}_History.csv"
START = "2004-01-01"
STALE_RUN = 5  # identical prints this many days in a row = stale feed


def _clean(s: pd.Series) -> pd.Series:
    """Drop non-positive prints and stale runs (repeated identical values)."""
    s = s.where(s > 0)
    run_id = (s != s.shift()).cumsum()
    run_len = s.groupby(run_id).cumcount()
    return s.where(run_len < STALE_RUN).dropna()


def fetch_cboe(symbol: str, refresh: bool = False) -> pd.Series:
    """Daily close of a CBOE index, cached to data/history/cboe_<symbol>.csv."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"cboe_{symbol}.csv")
    if refresh or not os.path.exists(path):
        r = requests.get(CBOE_URL.format(symbol), headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        with open(path, "w") as f:
            f.write(r.text)
    df = pd.read_csv(path)
    df["DATE"] = pd.to_datetime(df["DATE"], format="%m/%d/%Y")
    s = df.set_index("DATE").iloc[:, -1].astype(float)  # CLOSE, or the single value column
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return _clean(s).rename(symbol)


def fetch_prices(tickers, refresh: bool = False) -> pd.DataFrame:
    """Adjusted daily closes (date x ticker), cached to data/history/prices.csv."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, "prices.csv")
    if not refresh and os.path.exists(path):
        px = pd.read_csv(path, index_col=0, parse_dates=True)
        if set(tickers) <= set(px.columns):
            return px[list(tickers)]
    px = yf.download(list(tickers), start=START, auto_adjust=True, progress=False)["Close"]
    px.index = pd.to_datetime(px.index).tz_localize(None)
    px.to_csv(path)
    return px[list(tickers)]


@dataclass
class HistData:
    iv: pd.DataFrame        # date x ticker, 30d implied vol (decimal)
    prices: pd.DataFrame    # date x ticker, adjusted close
    spx_term: pd.DataFrame  # date x {VIX9D, VIX, VIX3M, VIX6M}, decimal
    extra: pd.DataFrame     # date x {VVIX, SKEW, COR1M, COR3M}, raw index points

    @property
    def returns(self) -> pd.DataFrame:
        """Daily log returns."""
        return np.log(self.prices / self.prices.shift(1))

    def realized_vol(self, window: int = 21) -> pd.DataFrame:
        """Trailing annualized realized vol (decimal) over `window` trading days."""
        return self.returns.rolling(window, min_periods=int(window * 0.8)).std() * np.sqrt(252)


def load_history(refresh: bool = False) -> HistData:
    """Load (and cache) the full historical dataset on a common trading calendar."""
    prices = fetch_prices(HIST_TICKERS, refresh)
    cal = prices.dropna(how="all").index

    iv = pd.concat({t: fetch_cboe(sym, refresh) for t, sym in VOL_INDEX.items()}, axis=1, sort=True) / 100
    spx_term = pd.concat({s: fetch_cboe(s, refresh) for s in SPX_TERM}, axis=1, sort=True) / 100
    extra = pd.concat({s: fetch_cboe(s, refresh) for s in SPX_EXTRA}, axis=1, sort=True)

    # Align to the equity trading calendar; no forward-filling (avoids stale values)
    return HistData(
        iv=iv.reindex(cal)[HIST_TICKERS],
        prices=prices.reindex(cal),
        spx_term=spx_term.reindex(cal),
        extra=extra.reindex(cal),
    )


if __name__ == "__main__":
    import sys
    h = load_history(refresh="--refresh" in sys.argv)
    for name, df in [("iv", h.iv), ("prices", h.prices), ("spx_term", h.spx_term), ("extra", h.extra)]:
        cov = df.notna().sum()
        first = df.apply(lambda c: c.first_valid_index())
        print(f"\n{name}:")
        for c in df.columns:
            print(f"  {c:6s} n={cov[c]:5d} from {first[c].date() if pd.notna(first[c]) else '-'}")
