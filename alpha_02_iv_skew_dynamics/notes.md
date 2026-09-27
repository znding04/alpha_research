# IV Skew Dynamics — Alpha Signal Notes

## Hypothesis

**Put-call IV skew (25-delta put IV minus 25-delta call IV) contains predictive information for forward equity returns.**

### Rationale

1. **Demand for downside protection** — Elevated put skew reflects institutional hedging demand. When skew steepens significantly, it may signal:
   - Near-term overbought conditions (fear of pullback)
   - Upcoming catalyst risk (earnings, macro events)
   - **Mean reversion signal**: Extreme skew → subsequent normalization → equity bounce

2. **Skew term structure** — The slope of skew across expirations (near-term vs far-term):
   - **Inverted skew term structure** (near > far): Acute near-term fear, potential short-term reversal
   - **Normal skew term structure** (near < far): Steady hedging demand, less predictive

3. **Cross-sectional ranking** — Ranking tickers by skew level/change:
   - Highest skew → most overbought/hedged → potential underperformance
   - Lowest skew (or negative) → complacency/confidence → potential outperformance

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `skew_25d` | `IV_put_25d - IV_call_25d` | Positive = put premium (fear) |
| `skew_term_slope` | `(far_skew - near_skew) / (far_dte - near_dte)` | Positive = normal term structure |
| `skew_change_1d` | `skew_25d(t) - skew_25d(t-1)` | Daily change in fear premium |

## Expected Behavior

| Regime | Skew Signal | Expected Forward Return |
|--------|-------------|------------------------|
| Risk-off / Fear | High positive skew | Mean reversion UP (short-term) |
| Risk-on / Complacency | Low/negative skew | Momentum UP (medium-term) |
| Skew inversion (near > far) | Term slope < 0 | Short-term bounce likely |
| Skew normalization | Term slope > 0 | Trend continuation |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: 2-180 DTE, focus on nearest 2-3 liquid expiries
- **Strikes**: ~25-delta approximations (0.95×spot for puts, 1.05×spot for calls)

## Implementation Notes

### Approximation Method
Since yfinance doesn't provide Greeks, 25-delta is approximated by moneyness:
- 25-delta put ≈ 5% OTM (strike ≈ 0.95 × spot)
- 25-delta call ≈ 5% OTM (strike ≈ 1.05 × spot)

This is a reasonable approximation for liquid large-cap names where IV smile is smooth.

### Known Limitations
1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **25-delta approximation** error varies with IV level and time to expiry
3. **Liquidity filter** may exclude informative illiquid strikes
4. **Single snapshot** — cannot compute `skew_change_1d` without history

## Results (2026-09-27)

| Ticker | Price | Near Skew | Far Skew | Term Slope | N Expirations |
|--------|-------|-----------|----------|------------|---------------|
| AAPL   | 341.07 | -0.0134 | 0.0012 | +0.000082 | 5 |
| SPY    | 771.35 | 0.0067 | 0.0156 | +0.000062 | 8 |
| QQQ    | 744.50 | 0.0031 | 0.0104 | +0.000051 | 7 |
| MSFT   | 516.17 | 0.0056 | 0.0148 | +0.000064 | 6 |
| GOOGL  | 343.92 | 0.0189 | 0.0254 | +0.000045 | 5 |
| AMZN   | 249.67 | 0.0112 | 0.0198 | +0.000057 | 6 |

**Observations:**
- All tickers show **normal term structure** (positive slope = far-term skew > near-term)
- AAPL has **negative near-term skew** (call premium > put premium) — unusual, suggests call buying / upside speculation
- SPY/GOOGL have highest absolute skew levels
- Term slopes are small but consistently positive across all names

## IC Analysis (Simulated)

With synthetic data (60 days, IC ~ 0.15-0.20):
- Rolling IC mean: ~0.18
- Information Ratio: ~1.2
- Win rate: ~58%
- Half-life: ~15 days

**Real IC pending historical data collection.**

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate skew time series
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Refine delta approximation** — Use Black-Scholes to solve for exact 25-delta strikes
4. **Test skew change signal** — `Δskew_1d` vs 1-5 day forward returns
5. **Combine with IV Rank** — Multi-factor: skew + IV rank + term structure

## Files

- `main.py` — Signal computation, outputs `data/iv_skew_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "The Volatility Surface" — Jim Gatheral (skew dynamics)
- "Option-Implied Risk-Neutral Distributions" — Bahra (1997)
- CBOE Skew Index (SKEW) methodology
- "Tail Risk and Asset Prices" — Kelly, Jiang (2014)