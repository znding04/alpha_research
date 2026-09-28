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

## Results (2026-09-28)

| Ticker | Price | Near IV (DTE) | Far IV (DTE) | Term Slope | Curvature | N Exp |
|--------|-------|---------------|--------------|------------|-----------|-------|
| AAPL   | 341.07 | — | — | — | — | <2 |
| SPY    | 771.35 | — | — | — | — | <2 |
| QQQ    | 744.50 | — | — | — | — | <2 |
| MSFT   | 516.17 | — | — | — | — | <2 |
| GOOGL  | 343.92 | 0.0156 (6d) | 0.0313 (38d) | +0.000488 | N/A | 2 |
| AMZN   | 249.67 | 0.0156 (8d) | 0.0156 (143d) | 0.000000 | N/A | 2 |

**Observations:**
- Only GOOGL and AMZN had ≥2 liquid expirations with valid ATM IV
- GOOGL shows **normal contango** (positive slope = IV rises with time)
- AMZN shows **flat term structure** (near IV ≈ far IV despite large DTE gap)
- AAPL, SPY, QQQ, MSFT had insufficient liquid expirations (likely due to strict liquidity filter)

**Liquidity filter issue**: Current filter `(volume > 10 or OI > 100)` per leg may be too strict for calls on some names. Consider relaxing or using combined call+put liquidity.

## IC Analysis (Simulated)

With synthetic data (60 days, negative correlation between slope and returns):
- Rolling IC mean: ~ -0.15 to -0.20
- Information Ratio: ~ -1.0 to -1.5
- Win rate: ~ 55-60%
- Half-life: ~ 10-15 days

**Interpretation**: Negative IC expected (backwardation → bounce). Real IC pending historical data collection.

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