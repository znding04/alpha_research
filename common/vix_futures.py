"""VIX futures data: CBOE monthly VX settlements → 30-day constant-maturity return series.

The constant-maturity (CM) series holds the first two monthly contracts with
weights that keep the average time to expiry at 30 calendar days, rebalanced
daily (same construction as the S&P 500 VIX Short-Term Futures index behind VXX/VIXY).
Daily return uses the same contracts on both days (no splicing across rolls).

Cached under data/history/vx/ (gitignored).
"""

import os
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests

from common.history import CACHE_DIR

VX_DIR = os.path.join(CACHE_DIR, "vx")
NEW_URL = "https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_{}.csv"
ARCHIVE_URL = "https://cdn.cboe.com/resources/futures/archive/volume-and-price/CFE_{}{}_VX.csv"
MONTH_CODES = "FGHJKMNQUVXZ"
TARGET_DAYS = 30
MIN_PRICE = 8.0


def _third_friday(y, m):
    d = date(y, m, 15)
    return d + timedelta(days=(4 - d.weekday()) % 7)


def vx_expiry(y, m):
    """Standard monthly VX expiry: the Wednesday 30 days before the 3rd Friday of the next month."""
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    return _third_friday(ny, nm) - timedelta(days=30)


def _download(y, m):
    """Settlement history for the contract expiring in (y, m). Tries holiday-shifted dates too."""
    os.makedirs(VX_DIR, exist_ok=True)
    path = os.path.join(VX_DIR, f"VX_{y}-{m:02d}.csv")
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=["date", "expiry"])
    exp = vx_expiry(y, m)
    hdr = {"User-Agent": "Mozilla/5.0"}
    text, used = None, None
    for shift in (0, -1, 1, -2):
        e = exp + timedelta(days=shift)
        r = requests.get(NEW_URL.format(e.isoformat()), headers=hdr, timeout=30)
        if r.ok and r.text.startswith("Trade Date"):
            text, used = r.text, e
            break
    if text is None:  # pre-2013 archive format
        r = requests.get(ARCHIVE_URL.format(MONTH_CODES[m - 1], str(y)[2:]), headers=hdr, timeout=30)
        if r.ok and r.text.startswith("Trade Date"):
            text, used = r.text, exp
    if text is None:
        return None
    from io import StringIO
    df = pd.read_csv(StringIO(text))
    df["date"] = pd.to_datetime(df["Trade Date"])
    px = df["Settle"].where(df["Settle"] > 0, df["Close"])
    out = pd.DataFrame({"date": df["date"], "price": px, "expiry": pd.Timestamp(used)})
    out = out[out.price > 0].sort_values("date")
    out.to_csv(path, index=False)
    return out


def load_vx_contracts(start_year=2009, end_year=None):
    """Long table: date, expiry, price for every monthly contract."""
    end_year = end_year or date.today().year + 1
    frames = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            if date(y, m, 1) > date.today() + timedelta(days=270):
                break
            df = _download(y, m)
            if df is not None and len(df):
                frames.append(df)
    return pd.concat(frames, ignore_index=True)


def constant_maturity_returns(contracts: pd.DataFrame) -> pd.DataFrame:
    """Daily return of the 30d CM long VIX futures position, plus its F1/F2 basis.

    Returns DataFrame indexed by date (the return is from that date's close to the next):
        cm_ret      next-day return of the CM position set at this close
        f1, f2      front / second contract settlements
        cm_price    interpolated 30d futures level
    """
    c = contracts[contracts.price >= MIN_PRICE]  # VIX futures have never settled below ~9; lower = bad print
    piv = c.pivot_table(index="date", columns="expiry", values="price")
    dates = piv.index
    rows = {}
    for i in range(len(dates) - 1):
        d0, d1 = dates[i], dates[i + 1]
        live = [e for e in piv.columns if e > d0 and pd.notna(piv.at[d0, e])]
        live.sort()
        if len(live) < 2:
            continue
        e1, e2 = live[0], live[1]
        t1, t2 = (e1 - d0).days, (e2 - d0).days
        if t1 > 40 or t2 > 75:  # front month missing from the data that day
            continue
        w1 = np.clip((t2 - TARGET_DAYS) / (t2 - t1), 0, 1)
        p10, p20 = piv.at[d0, e1], piv.at[d0, e2]
        p11, p21 = piv.at[d1, e1], piv.at[d1, e2]
        if e1 <= d1 or pd.isna(p11):  # front expires overnight: settle at the next listed price if any
            p11 = p11 if pd.notna(p11) else p10
        if pd.isna(p21):
            continue
        rows[d0] = {
            "cm_ret": w1 * (p11 / p10 - 1) + (1 - w1) * (p21 / p20 - 1),
            "f1": p10, "f2": p20, "t1": t1, "t2": t2,
            "cm_price": w1 * p10 + (1 - w1) * p20,
        }
    return pd.DataFrame.from_dict(rows, orient="index").sort_index()
