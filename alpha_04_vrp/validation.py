"""Tradability validation of alpha_04 (see common/validation.py for the shared pass rule).

PRE-REGISTERED 2026-10-20, before any strategy / alpha numbers for this signal were computed.
Signal     : 21d-realized-vol VRP, per name (CBOE 30d vol index of each underlying), at close t.
Why        : its historical IC vs forward ΔIV is large and negative (IV mean reversion), but ΔIV
             is not a return. The question is whether that survives as option P&L.
Primary    : cross-section of 5-day delta-hedged 30d ATM straddles on the 17-name universe,
             rank-weighted long/short, non-overlapping weekly periods, 3% of premium round trip.
Controls   : equal-weight short straddles (the unconditional VRP harvest); IV-level cross-sectional
             long/short (is it just "sell the richest IV"?).
Secondary  : timing 30d VIX futures with the SPX value of the signal; controls VIX level, futures basis.
"""

from alpha_04_vrp.historical import compute_signal
from common import instruments as I
from common.validation import Test

NAME = "VRP (IV² − RV²)"


def build(data):
    sig = compute_signal(data)
    vix = data.spx_term["VIX"]
    return [
        Test("alpha_04", "cross_section", sig, I.hedged_straddles(data), {"iv_level": data.iv}),
        Test("alpha_04", "timing", sig["SPY"], I.vix_futures(),
             {"vix_level": vix, "futures_basis": I.futures_basis(data)}, primary=False),
    ]
