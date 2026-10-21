# Tradability Validation

Pre-registered test per alpha (design in each `alpha_*/validation.py`, rule in `common/validation.py`). In-sample ≤ 2018-12-31 (only the trade direction is chosen there), out-of-sample ≥ 2019-01-01, after costs, 1-day execution lag. **Pass** = OOS IC with the in-sample sign and |t| ≥ 2, **and** positive OOS alpha (NW t ≥ 2) after regressing on every benchmark strategy. Only the primary test decides; secondary tests are context.

| Alpha | Signal | Test | Instrument | IS IC | OOS IC (t) | OOS alpha /yr (t) | OOS net ret /yr (Sharpe) | OOS gross Sharpe | Break-even cost (assumed) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| alpha_03_iv_term_structure | IV term structure (VIX3M/VIX − 1) | primary | 30d VIX futures | +0.062 | +0.149 (+3.0) | +6.1% (+1.5) | -9.7% (+0.07) | +0.20 | 0.21% (0.13%) | ❌ FAIL |
| alpha_03_iv_term_structure | IV term structure (VIX3M/VIX − 1) | secondary | VIXY | +0.035 | +0.155 (+3.1) | +5.7% (+1.5) | -6.5% (+0.14) | +0.20 | 0.22% (0.05%) | fail |
| alpha_04_vrp | VRP (IV² − RV²) | primary | delta-hedged straddles (15 names) | -0.023 | -0.030 (-2.0) | -149.5% (-5.0) | -72.2% (-3.54) | +0.89 | 0.61% (3.00%) | ❌ FAIL |
| alpha_04_vrp | VRP (IV² − RV²) | secondary | 30d VIX futures | -0.090 | -0.023 (-0.5) | -8.1% (-0.5) | -16.2% (-0.05) | +0.06 | 0.07% (0.13%) | fail |
| alpha_05_iv_rank_percentile | IV percentile (252d) | primary | delta-hedged straddles (15 names) | -0.055 | -0.083 (-5.0) | -120.6% (-5.4) | -68.6% (-3.57) | +1.35 | 0.82% (3.00%) | ❌ FAIL |
| alpha_05_iv_rank_percentile | IV percentile (252d) | secondary | 30d VIX futures | -0.070 | -0.086 (-1.7) | -13.6% (-2.0) | -27.3% (-0.30) | -0.21 | -0.30% (0.13%) | fail |
| alpha_07_iv_dispersion | SPX implied correlation (COR3M) | primary | SPY | +0.107 | +0.112 (+2.2) | +2.0% (+0.9) | +2.3% (+0.22) | +0.25 | 0.11% (0.01%) | ❌ FAIL |
| alpha_07_iv_dispersion | SPX implied correlation (COR3M) | secondary | 30d VIX futures | -0.145 | -0.157 (-3.1) | +26.0% (+1.9) | +4.0% (+0.34) | +0.42 | 0.67% (0.13%) | fail |
| alpha_12_iv_momentum | IV momentum (5d) | primary | delta-hedged straddles (15 names) | -0.036 | -0.064 (-3.7) | -167.5% (-4.1) | -76.6% (-3.20) | +0.52 | 0.42% (3.00%) | ❌ FAIL |
| alpha_12_iv_momentum | IV momentum (5d) | secondary | 30d VIX futures | -0.099 | -0.076 (-1.5) | -2.5% (-0.2) | -10.3% (+0.04) | +0.23 | 0.15% (0.13%) | fail |

IC horizon: 5d forward return for timing tests, one 5-day period for cross-section tests. Break-even cost = OOS gross mean return / mean turnover: the cost per unit traded (fraction of notional; of straddle premium for the panel, round trip) at which the net return is zero. Grids: `results/validation/`. Charts: `figures/validation/`.
