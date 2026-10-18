"""Historical term-structure signal: SPX 3-month IV / 1-month IV − 1 (VIX3M / VIX − 1).

Positive = contango, negative = backwardation. SPX only → SPY time-series test.
"""

NAME = "SPX IV term ratio (VIX3M/VIX − 1)"
HYPOTHESIS = -1  # notes.md: backwardation (low ratio) → bounce


def compute_signal(data):
    t = data.spx_term
    return (t["VIX3M"] / t["VIX"] - 1).to_frame("SPY")
