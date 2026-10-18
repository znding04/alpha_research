"""Historical VRP signal: 30d implied variance minus trailing 21d realized variance.

IV = CBOE 30-day vol index for each underlying (VIX for SPY, VXAPL for AAPL, ...).
Run via: python3 run_historical.py alpha_04
"""

NAME = "VRP (IV² − RV²)"
HYPOTHESIS = +1  # notes.md: high VRP (expensive options / fear) → higher forward returns


def compute_signal(data):
    rv = data.realized_vol(21)
    return data.iv ** 2 - rv ** 2
