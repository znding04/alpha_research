# IV Skew Term Structure Composite — Alpha 29

## Hypothesis

**The interaction between IV skew dynamics and IV term structure slope captures stress vs. complacency regimes that predict forward returns.**

Two stress indicators:
1. **Backwardation** — near-term IV > far-term IV (fear in the front end)
2. **Steepening skew** — put-call skew increases with maturity (tail-hedge demand shifting out along the curve)

**Composite signal** = (skew slope per day) × (normalized term slope per month)

- **Negative combined score** → backwardation + steepening skew → stress regime → potential mean-reversion long opportunity
- **Positive combined score** → contango + flattening/inverted skew → calm regime → potential underweight/short

Cross-sectionally rank tickers by combined score each snapshot date; most negative = highest stress signal.

## Signal Definition

| Step | Rule |
|------|------|
| Near expiration | Target ~30 DTE, within ±15 days, min 15 DTE, max 90 DTE |
| Far expiration | Target ~75 DTE, within ±20 days, min 15 DTE, max 90 DTE |
| Liquidity filter | volume > 5 OR OI > 50; 0.03 < IV < 3.0; ≥5 contracts |
| Skew metric | Approx 25-delta put IV minus call IV (nearest OTM strikes) |
| Term slope | (far ATM IV - near ATM IV) / (far DTE - near DTE) |
| Normalized term slope | term slope × 30 / near ATM IV (percent per month) |
| Signal | skew_slope_per_day × normalized_term_slope |

## Files

- `main.py` — computes the signal, writes `data/iv_skew_term_structure_latest.csv`
- `ic_analysis.py` — cross-sectional IC test against forward returns + synthetic rolling-IC demo

## Results (2026-11-01)

Composite signal ran on universe `{ETFS + SINGLE_NAMES}` from `common/universe.py`. Raw output: `data/iv_skew_term_structure_latest.csv`.

**Interpretation guide:**

| Combined Score | Regime | Trading Implication |
|---------------|--------|-------------------|
| Most negative (< -2σ) | Severe stress: backwardation + steepening skew | Potential mean-reversion long |
| Negative (-2σ to -1σ) | Moderate stress | Neutral-to-long bias |
| Near zero | Mixed signals | No directional bias |
| Positive (+1σ to +2σ) | Moderate calm: contango + flattening skew | Neutral-to-short bias |
| Most positive (> +2σ) | Severe complacency | Potential underweight/short |

## Caveats

- Skew metric uses nearest-OTM approximation rather than full Black-Scholes delta interpolation; refine for production
- 25-delta OTM strikes may not exist for all expirations/tickers; falls back to nearest available
- Single-snapshot IC is below `compute_ic`'s meaningful minimum (≥10 observations needed)
- Full validation requires accumulated daily snapshots for rolling IC analysis
