"""Historical VRP term slope: far VRP − near VRP on SPX.

near VRP = VIX9D² − RV(10d)², far VRP = VIX3M² − RV(63d)². SPX only → SPY time-series test.
"""

NAME = "SPX VRP term slope (far − near)"
HYPOTHESIS = -1  # notes.md: vrp_slope expected negative IC (inverted term → bounce)


def compute_signal(data):
    t = data.spx_term
    near = t["VIX9D"] ** 2 - data.realized_vol(10)["SPY"] ** 2
    far = t["VIX3M"] ** 2 - data.realized_vol(63)["SPY"] ** 2
    return (far - near).to_frame("SPY")
