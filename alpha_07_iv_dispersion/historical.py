"""Historical dispersion signal: CBOE 3-month implied correlation (COR3M).

Index IV vs constituent IV is driven by implied correlation; COR3M is CBOE's
clean version of the same spread (SPX vs its top-50 constituents). SPY time-series test.
"""

NAME = "SPX implied correlation (COR3M)"
HYPOTHESIS = +1  # notes.md: index IV rich vs constituents = fear premium → mean reversion UP


def compute_signal(data):
    return data.extra[["COR3M"]].rename(columns={"COR3M": "SPY"})
