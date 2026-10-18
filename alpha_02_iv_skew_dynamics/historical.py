"""Historical skew signal: CBOE SKEW index (SPX risk-neutral skewness from OTM puts).

Proxy for the 25Δ put-call skew; only exists for SPX, so this is a SPY time-series test.
"""

NAME = "SPX skew (CBOE SKEW)"
HYPOTHESIS = +1  # notes.md: high put skew (fear) → mean reversion UP


def compute_signal(data):
    return data.extra[["SKEW"]].rename(columns={"SKEW": "SPY"})
