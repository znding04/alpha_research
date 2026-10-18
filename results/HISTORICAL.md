# Historical IC Summary

Data: CBOE implied-vol indices + yfinance prices, through 2026-10-16. Signal at close t, forward window starts at close t+1. `cs` = daily cross-sectional rank IC across the ETF/single-name universe (NW t-stat); `ts` = time-series rank IC per underlying, averaged (t ≈ IC·√(N/h)). Hypothesis = expected IC sign vs forward returns from each alpha's notes.md.

| Alpha | Kind | Hyp. | IC (21d ret) | t | IC post-2019 | IC (21d ΔIV) | t | Verdict |
|---|---|---|---|---|---|---|---|---|
| alpha_02_iv_skew_dynamics | ts | + | -0.020 | -0.3 | -0.121 | +0.124 | +2.0 | ❌ not significant |
| alpha_03_iv_term_structure | ts | − | -0.195 | -2.8 | -0.255 | +0.431 | +6.1 | ✅ significant, as hypothesized |
| alpha_04_vrp | cs | + | +0.007 | +0.4 | +0.035 | -0.144 | -9.5 | ❌ not significant |
| alpha_05_iv_rank_percentile | cs | + | -0.010 | -0.6 | -0.002 | -0.353 | -24.8 | ❌ not significant |
| alpha_06_vrp_term_structure | ts | − | -0.041 | -0.6 | -0.072 | +0.018 | +0.3 | ❌ not significant |
| alpha_07_iv_dispersion | ts | + | +0.120 | +1.9 | +0.213 | -0.252 | -4.0 | ❌ not significant |
| alpha_11_vol_of_vol | cs | − | +0.028 | +1.7 | -0.005 | +0.003 | +0.2 | ❌ not significant |
| alpha_12_iv_momentum | cs | − | -0.007 | -0.9 | -0.008 | -0.142 | -16.3 | ❌ not significant |
| alpha_13_iv_skew_momentum | ts | − | +0.008 | +0.1 | +0.015 | +0.018 | +0.3 | ❌ not significant |
| alpha_15_iv_term_momentum | ts | + | -0.007 | -0.1 | +0.002 | +0.132 | +1.9 | ❌ not significant |

Full grid (1/5/21d, both targets, cs and ts): `results/historical_ic.csv`. Charts: `figures/historical/`.
