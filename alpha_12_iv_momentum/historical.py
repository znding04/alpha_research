"""Historical IV momentum: 5-day % change in 30d IV."""

NAME = "IV momentum (5d)"
HYPOTHESIS = -1  # notes.md: rising IV predicts downside


def compute_signal(data):
    return data.iv / data.iv.shift(5) - 1
