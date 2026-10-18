# IV Term Structure Slope — Alpha Signal Notes

## Hypothesis

**The slope of the ATM IV term structure (short-dated vs long-dated IV) contains predictive information for forward equity returns.**

### Rationale

1. **Volatility mean reversion** — IV term structure reflects market expectations of future volatility:
   - **Contango (positive slope)**: IV rises with time → normal, complacent market → trend continuation
   - **Backwardation (negative slope)**: Near-term IV > far-term IV → acute stress/fear → mean reversion bounce likely

2. **Volatility risk premium dynamics** — The term structure slope captures the pricing of near-term vs far-term uncertainty:
   - Steep backwardation = expensive near-term protection = oversold/panic
   - Flat/steep contango = cheap near-term protection = complacency/trend

3. **Cross-sectional ranking** — Ranking tickers by term slope:
   - Most negative slope (backwardation) → highest fear → potential short-term outperformance (mean reversion)
   - Most positive slope (steep contango) → lowest fear → potential underperformance (complacency)

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `term_slope` | `(IV_far - IV_near) / (DTE_far - DTE_near)` | Positive = contango, Negative = backwardation |
| `term_curvature` | 2nd derivative approx (3+ expiries) | Convexity of term structure |
| `near_atm_iv` | ATM IV at shortest DTE | Near-term vol level |
| `iv_spread` | `near_atm_iv - far_atm_iv` | Simple near-far difference |

## Expected Behavior

| Regime | Term Slope | Expected Forward Return |
|--------|------------|------------------------|
| Risk-off / Panic | Negative (backwardation) | Mean reversion UP (1-5 days) |
| Risk-on / Complacent | Positive (steep contango) | Momentum UP or flat (medium-term) |
| Normal | Slightly positive | No strong signal |
| Transition | Slope sign change | Regime shift warning |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: Minimum 2 liquid expiries within 180 DTE
- **Strikes**: ATM (strike closest to spot)
- **Liquidity filter**: Volume > 10 or OI > 100 per leg

## Implementation Notes

### ATM IV Calculation
For each expiration, ATM IV is computed as the average of call and put IV at the strike closest to spot. If only one side is liquid, use that side.

### Slope Calculation
```
term_slope = (IV_far - IV_near) / (DTE_far - DTE_near)
```
Units: IV points per day. Typical range: -0.005 to +0.005.

### Known Limitations
1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **Sparse expirations** — Some tickers have few liquid expiries, limiting slope precision
3. **ATM approximation** — Using nearest strike introduces small error, especially for high-priced names
4. **Single snapshot** — Cannot compute slope change without history
5. **Market hours bias** — Bid/ask often 0 after hours; relies on lastPrice-derived IV

## Results (2026-10-16 close, run 2026-10-18)

| Ticker | Price | Near IV (DTE) | Far IV (DTE) | Term Slope (/day) | Curvature | N Exp |
|--------|-------|---------------|--------------|-------------------|-----------|-------|
| AAPL   | 343.46 | 0.2514 (0d) | 0.2767 (179d) | +0.000142 | -1.60e-05 | 15 |
| SPY    | 763.25 | 0.1390 (0d) | 0.1616 (163d) | +0.000138 | -4.5e-07 | 22 |
| QQQ    | 709.80 | 0.2366 (0d) | 0.2275 (163d) | -0.000056 | -8.7e-07 | 20 |
| MSFT   | 529.05 | 0.2434 (0d) | 0.3098 (179d) | +0.000371 | -3.87e-05 | 13 |
| GOOGL  | 340.59 | 0.3185 (0d) | 0.3621 (179d) | +0.000244 | -1.60e-05 | 14 |
| AMZN   | 250.00 | 0.2871 (0d) | 0.3724 (179d) | +0.000476 | -6.39e-05 | 15 |

Raw per-expiration ATM IVs: `data/iv_term_structure_latest.csv`.

**Observations:**
- All 6 tickers now have full term structures (13–22 expirations); the earlier "<2 expirations" problem and the 0.0156 placeholder IVs from the 2026-09-28 run are gone (that table was discarded).
- Contango for 5/6 names; QQQ is the only name in mild backwardation (slope < 0).
- AMZN, GOOGL and MSFT show a clear IV hump at the 10-30 expiry (AMZN 0.52, GOOGL 0.48, MSFT 0.41 vs ~0.30–0.37 elsewhere) — earnings events sitting in that expiry. This distorts slope/curvature; earnings expirations should be excluded or event-vol stripped.
- "Near" = 0 DTE because the run was on a weekend (next expiry 10-19). 0-DTE IV is noisy; use a minimum DTE (e.g. ≥7d) for the near leg.
- All names classified FLAT by the script's thresholds — thresholds may need recalibration to the per-day slope scale.

## IC Analysis (Simulated)

With synthetic data (60 days, negative correlation between slope and returns):
- Rolling IC mean: ~ -0.15 to -0.20
- Information Ratio: ~ -1.0 to -1.5
- Win rate: ~ 55-60%
- Half-life: ~ 10-15 days

**Interpretation**: Negative IC expected (backwardation → bounce).

**⚠️ These are synthetic demo numbers, not evidence of predictive power.** `simulate_rolling_ic()` generates returns as `signal * k + noise`, so a positive/negative IC is baked in by construction. Separately, `run_ic_analysis()` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and cannot test predictability.

**Real IC: not yet measured.** Requires daily signal snapshots (≥30–60 trading days) paired with true forward returns.

## Next Steps

1. **Relax liquidity filter** — Use combined call+put volume/OI, or lower thresholds
2. **Build historical database** — Run `main.py` daily via cron to accumulate term structure time series
3. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
4. **Test slope change signal** — `Δterm_slope_1d` vs 1-5 day forward returns
5. **Combine with IV Rank & Skew** — Multi-factor: term slope + IV rank + skew dynamics
6. **Add VIX term structure** — For SPY, incorporate VIX futures term structure as benchmark

## Files

- `main.py` — Signal computation, outputs `data/iv_term_structure_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "The Volatility Surface" — Jim Gatheral (term structure dynamics)
- "Volatility Term Structure and Risk Premia" — Mixon (2007)
- CBOE VIX Term Structure (VIX9D, VIX, VIX3M, VIX6M)
- "Term Structure of Volatility Risk Premia" — Dew-Becker et al. (2017)