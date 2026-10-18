"""Historical term-structure momentum: 5-day change in VIX3M/VIX. SPY time-series test."""

NAME = "SPX term momentum (Δ VIX3M/VIX 5d)"
HYPOTHESIS = +1  # notes.md: steepening toward contango = normalization → risk-on


def compute_signal(data):
    r = data.spx_term["VIX3M"] / data.spx_term["VIX"]
    return (r - r.shift(5)).to_frame("SPY")
