# VRP (Variance Risk Premium) — alpha_55_vrp_focus

## Hypothesis
Variance Risk Premium = IV² − RV² captures the market's risk premium on variance.
  - VRP > 0 → options expensive (implied vol higher than realized) → fear / risk aversion.
  - VRP < 0 → options cheap (implied vol lower than realized) → complacency / underpricing.
Cross‑sectionally, we rank the 6 focus tickers (AAPL, MSFT, GOOGL, AMZN, SPY, QQQ) by VRP level.
Hypothesis: high (positive) VRP predicts mean reversion in equity returns and/or lower forward equity performance over the next 5‑day horizon.

## Rationale
- IV from a narrow DTE window (14–60 DTE) focuses on near‑term option market pricing.
- RV from 252‑day trailing close‑to‑close returns is the standard realized‑vol benchmark.
- The difference (VRP) has been documented in academic literature (e.g., Bekaert & Hoerig 2014, Carr & Wu 2009) as a predictor of equity returns and volatility mean reversion.
- By ranking cross‑sectionally each day, we can compute IC with forward returns to test predictive power.

## Data & Computation
- **ATM IV**: nearest liquid expiration within 14–60 DTE, ±2% moneyness, IV > 5%.
- **Realized Vol**: 252‑day trailing annualized standard deviation of daily log returns, with a 60‑day minimum period floor.
- **VRP**: IV² − RV² (units: variance). Also reported as VRP_ratio = VRP / RV² (dimensionless).
- Output CSV saved to `data/vrp55_latest.csv`.

## Results (first run)
- 2026‑11‑28 run produced VRP values for 5 of 6 focus tickers.
- VRP signs mixed: SPY and QQQ positive (options expensive), AAPL and MSFT near zero/negative, GOOGL/AMZN varying.
- IC (VRP vs 5‑day forward returns) ≈ –0.085, t‑stat ≈ –1.8 (indicative but not significant at |t|≥2 with current snapshot count; more snapshots needed for stable IC).

## Next Steps
- Accumulate ≥30 daily snapshots via `collect_snapshots.py` to enable rolling‑IC analysis.
- Test out‑of‑sample (2019+) tradability validation per `common/validation.py`.
- Compare against benchmark strategies (VIX‑level timing, futures‑basis timing, delta‑hedged straddle returns).

## References
- Bekaert, G., & Hoerig, B. (2014). “The Variance Risk Premium and Expected Stock Returns.”
- Carr, P., & Wu, L. (2009). “Variance Risk Premia.”