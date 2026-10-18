"""Historical vol-of-vol: 20-day realized vol of daily log changes in 30d IV (annualized)."""

import numpy as np

NAME = "Vol-of-vol (20d)"
HYPOTHESIS = -1  # notes.md: high VoV = risk-off → lower returns (and higher future vol)


def compute_signal(data):
    d = np.log(data.iv / data.iv.shift(1))
    return d.rolling(20, min_periods=16).std() * np.sqrt(252)
