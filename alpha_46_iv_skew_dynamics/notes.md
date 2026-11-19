# Alpha 46 — Cross-Sectional IV Skew (25Δ put-call) Rank

## Hypothesis

**Cross-sectional skew rank predicts forward equity returns over 5–21 days.**  
A high skew rank (near 1.0) signals extreme put‑putting / hedging demand, which can indicate:
- Fear‑driven positioning that may reverse (mean reversion → lower forward returns)
- Or event‑setup premium priced in (bullish → higher forward returns)

Let the IC decide the sign; the more parsimonious hypothesis is **negative**: extreme fear (high skew) predicts lower forward returns as hedging pressure abates.

## Signal Definition

| Step | Calculation |
|------|-------------|
| **Near / Far tenors** | ~30 DTE (near) and ~75 DTE (far) nearest available expirations |
| **25Δ put IV** | Black‑Scholes delta interpolation on OTM put chain to find IV at |δ|=0.25 |
| **25Δ call IV** | Same on call chain |
| **Skew_25d** | `put_25d_iv − call_25d_iv` (positive = put premium / fear) |
| **Cross‑sectional rank** | `rank( skew_25d )` across the 6 focus names (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN); 1.0 = richest put fear |
| **Signal value** | `skew_rank` (0.0–1.0 percentile) |

## Rationale

- **Skew is orthogonal to term structure slope** (alpha_03 / 27 / 37) and **orthogonal to IV rank percentile** (alpha_05 / 43). Those measure vertical/horizontal IV dimensions; skew measures put‑vs‑call asymmetry.
- **Cross-sectional rank** makes the signal comparable across tickers with vastly different IV levels.
- **Extreme skew historically precedes mean‑reversion**: when put‑premium is at the extreme right tail, dealer hedging pressure tends to dissipate, often coinciding with a return bounce or drop depending on the regime.

## Data Source

**Source:** yfinance option chains (real‑time, 02:00 ET cron snapshot) for the 6 focus tickers.  
**Lag:** 02:00 ET may capture market‑closed degenerate IVs (0.0625 default). Best run post‑market close (22:00 ET+).

## Output

- `data/iv_skew_dynamics_46_latest.csv` — cross‑sectional skew rank + levels per ticker.
- `data/iv_skew_dynamics_46_latest.csv` columns: ticker, current_price, near_skew_25d, far_skew_25d, skew_25d, skew_rank, n_expirations.

## Historical Note (for future snapshot accumulation)

As more daily snapshots accumulate in `data/snapshots/YYYY‑mm‑dd/`, a rolling‑IC analysis can test whether **deviations from the rolling skew‑rank mean** (rather than the raw percentile) are more predictive. TBD.