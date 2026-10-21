"""Tradability validation of alpha_07 (see common/validation.py for the shared pass rule).

PRE-REGISTERED 2026-10-20, before any strategy / alpha numbers for this signal were computed.
Signal     : CBOE 3-month SPX implied correlation (COR3M) at close t.
Hypothesis : high implied correlation = index fear premium → SPX return mean-reverts up (notes.md).
Primary    : timing SPY (the hypothesis is about the index return). 1 bp per unit traded.
Controls   : buy & hold SPY; VIX-level timing (COR3M co-moves with VIX: is it just "buy when VIX high"?).
Secondary  : 30d VIX futures timing (COR3M also has a strong −ΔIV IC), controls VIX level + basis.
Caveat     : the post-2019 spot-return IC (+0.21) was already seen in run_historical.py, so OOS is
             not fully untouched; the strategy, benchmarks and alpha regression were not.
"""

from alpha_07_iv_dispersion.historical import compute_signal
from common import instruments as I
from common.validation import Test

NAME = "SPX implied correlation (COR3M)"


def build(data):
    sig = compute_signal(data)["SPY"]
    vix = data.spx_term["VIX"]
    return [
        Test("alpha_07", "timing", sig, I.spy(data), {"vix_level": vix}),
        Test("alpha_07", "timing", sig, I.vix_futures(),
             {"vix_level": vix, "futures_basis": I.futures_basis(data)}, primary=False),
    ]
