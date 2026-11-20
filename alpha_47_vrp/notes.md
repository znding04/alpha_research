# Alpha 47 — VRP (Variance Risk Premium) Cross-Sectional Signal

## Hypothesis

**Cross-sectional VRP (IV² − RV²) predicts forward equity returns over 5–21 days.** VRP = variance risk premium: the gap between option-implied variance and realized variance. Positive VRP = options expensive relative to realized move (fear premium). Cross-sectionally, names with the highest VRP carry the richest protection demand and the largest harvestable premium.

Sign is left to the IC: the classic hypothesis is **positive** (high VRP → higher forward returns as the premium is earned / fear mean-reverts), but stress regimes can invert it.

## Signal Definition

| Step | Calculation |
|------|-------------|
| **ATM IV** | Liquidity-weighted mean IV of calls+puts with strike within ±5% of spot, nearest expiry in 14–60 DTE, IV in (0.01, 3.0), volume>10 or OI>100 |
| **Realized vol (RV)** | 30-day std of daily log returns × √252 |
| **VRP variance** | `IV² − RV²` (primary signal) |
| **VRP vol points** | `sign(VRP)·√|VRP|` |
| **VRP ratio** | `IV² / RV²` (>1 = IV above RV) |

## Rationale

- VRP is a classic equity risk premium (Carr-Wu 2009, Bollerslev-Tauchen-Zhou 2009): options are systematically priced above realized vol.
- Cross-sectional rank makes the signal comparable across names with different IV levels.
- Orthogonal to pure IV-level alphas (05/43): VRP normalizes by realized vol, isolating the *premium* not the *level*.

## Data Source

yfinance option chains + daily history, 6 focus names (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN) plus the broader ETF universe in `common/universe.py`.

**Caveat:** a 02:00 ET cron snapshot may capture market-closed degenerate IVs (0.0156 / 0.0625 yfinance placeholders). Best run after market close.

## Output

- `data/vrp_latest.csv` — columns: ticker, current_price, atm_iv, realized_vol, iv_variance, rv_variance, vrp_variance, vrp_vol_points, vrp_ratio

## IC Analysis

- **Real IC: pending.** One snapshot is below `compute_ic`'s 10-observation minimum. `ic_analysis.py` uses true forward returns (no look-ahead) via `common.utils.forward_return`, and correctly reports "not available" for a fresh snapshot — real IC needs ≥30–60 daily snapshots pooled over time.

## Caveats & Known Issues

- **Earnings contamination:** single-name ATM IV from the nearest 14–60 DTE expiry can straddle earnings, inflating VRP with event premium. Index ETFs (SPY, QQQ) are the cleanest readings until an earnings filter is added.
- **Degenerate IVs at 02:00 ET:** the market-closed snapshot produced sub-0.05 ATM IVs in this run (IV² ≪ RV² → all deeply negative VRP). A post-close run should give sensible positive VRP. This run's absolute levels are not trustworthy; the pipeline is.
- Single expiry ignores term structure — see alpha_06 (VRP term structure) for that dimension.

## References

- Carr & Wu (2009), "Variance Risk Premiums"
- Bollerslev, Tauchen & Zhou (2009), "Expected Stock Returns and Variance Risk Premia"
- Bekaert & Hoerova (2014), "The VIX, the variance premium and stock market volatility"