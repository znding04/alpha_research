"""Tradability validation of alpha_03 (see common/validation.py for the shared pass rule).

PRE-REGISTERED 2026-10-18 (first run: vix_futures_test.py; ported unchanged to the shared pipeline)
Signal     : VIX3M / VIX − 1 at close t.
Primary    : timing 30d constant-maturity VIX futures. The signal's strongest IC is vs ΔIV, and
             VIX futures are the cleanest tradable claim on 30d SPX implied vol.
Controls   : VIX-level timing, futures-basis timing (CM futures / VIX − 1), always short.
Secondary  : VIXY (tradable ETF, fees + borrow), not scored.
"""

from alpha_03_iv_term_structure.historical import compute_signal
from common import instruments as I
from common.validation import Test

NAME = "IV term structure (VIX3M/VIX − 1)"


def build(data):
    sig = compute_signal(data)["SPY"]
    controls = {"vix_level": data.spx_term["VIX"], "futures_basis": I.futures_basis(data)}
    return [
        Test("alpha_03", "timing", sig, I.vix_futures(), controls),
        Test("alpha_03", "timing", sig, I.vixy(), controls, primary=False),
    ]
