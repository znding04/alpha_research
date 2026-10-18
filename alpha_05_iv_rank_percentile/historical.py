"""Historical IV percentile: rank of today's 30d IV within its trailing 252-day window."""

NAME = "IV percentile (252d)"
HYPOTHESIS = +1  # notes.md: IV > 80th pctl (fear) → mean reversion UP


def compute_signal(data):
    return data.iv.rolling(252, min_periods=200).apply(lambda x: (x <= x[-1]).mean(), raw=True)
