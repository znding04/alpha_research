"""Historical skew momentum: 5-day change in the CBOE SKEW index. SPY time-series test."""

NAME = "SPX skew momentum (ΔSKEW 5d)"
HYPOTHESIS = -1  # notes.md: skew steepening = informed downside positioning


def compute_signal(data):
    s = data.extra["SKEW"]
    return (s - s.shift(5)).to_frame("SPY")
