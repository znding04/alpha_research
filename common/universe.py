"""Ticker universe shared by all alphas.

Live snapshot universe (yfinance option chains) = major ETFs + single names.
Historical universe = underlyings with a CBOE 30-day implied-vol index
(daily history since ~2011), used for time-series / cross-sectional IC.
"""

ETFS = ["SPY", "QQQ", "IWM", "DIA", "GLD", "SLV", "TLT", "EEM", "EWZ", "FXI", "GDX", "USO"]
SINGLE_NAMES = ["AAPL", "MSFT", "GOOGL", "AMZN"]

# Live snapshot universe used by every alpha_*/main.py
TICKERS = ETFS + SINGLE_NAMES

# CBOE 30-day implied vol index per underlying.
# SPY/QQQ/IWM/DIA map to their index vol (SPX/NDX/RUT/DJIA) — close proxies.
VOL_INDEX = {
    "SPY": "VIX",
    "QQQ": "VXN",
    "IWM": "RVX",
    "DIA": "VXD",
    "GLD": "GVZ",
    "SLV": "VXSLV",
    "TLT": "VXTLT",
    "EEM": "VXEEM",
    "EWZ": "VXEWZ",
    "FXI": "VXFXI",
    "GDX": "VXGDX",
    "USO": "OVX",
    "AAPL": "VXAPL",
    "AMZN": "VXAZN",
    "GOOGL": "VXGOG",
    "GS": "VXGS",
    "IBM": "VXIBM",
}

# Historical universe (no CBOE vol index exists for MSFT)
HIST_TICKERS = list(VOL_INDEX)

# SPX implied-vol term structure: index -> constant maturity in calendar days
SPX_TERM = {"VIX9D": 9, "VIX": 30, "VIX3M": 93, "VIX6M": 182}

# Other CBOE series used by SPX-only signals
SPX_EXTRA = ["VVIX", "SKEW", "COR1M", "COR3M"]
