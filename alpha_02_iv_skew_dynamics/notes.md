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

## Results (2026-10-16 close, run 2026-10-18)

| Ticker | Price | Near Skew (exp, DTE) | Far Skew | Term Slope | N Expirations |
|--------|-------|----------------------|----------|------------|---------------|
| AAPL   | 343.46 | +0.0193 (11-27, 39d) | — | — | 1 |
| SPY    | 763.25 | +0.0172 (02-26, 130d) | — | — | 1 |
| QQQ    | 709.80 | +0.1533 (10-22, 3d) | — | — | 1 |
| MSFT   | 529.05 | — | — | — | 0 |
| GOOGL  | 340.59 | +0.0513 (10-23, 4d) | -0.0580 (04-16, 179d) | -0.000624 | 3 |
| AMZN   | 250.00 | — | — | — | 0 |

Skew = 25Δ put IV − 25Δ call IV. Raw: `data/iv_skew_latest.csv`.

**Observations:**
- Coverage is poor: MSFT and AMZN produced no valid expiration, and only GOOGL had ≥2 expirations, so term slope exists for one name only. The liquidity/strike filters in `main.py` are too strict and need relaxing before this signal is usable cross-sectionally.
- The "near" expiration differs a lot by ticker (3d for QQQ vs 130d for SPY), so near-skew values are not comparable across names as-is — pick a fixed DTE bucket.
- QQQ's 3-DTE skew (0.153) is dominated by very short-dated put demand; not representative of 30d skew.
- GOOGL's skew flips sign with tenor (put premium near-term, call premium far-term).
- The previous 2026-09-27 table was discarded: it contained yfinance placeholder IVs (e.g. 0.0156) and is not reliable.

## IC Analysis (Simulated)

With synthetic data (60 days, IC ~ 0.15-0.20):
- Rolling IC mean: ~0.18
- Information Ratio: ~1.2
- Win rate: ~58%
- Half-life: ~15 days

**⚠️ These are synthetic demo numbers, not evidence of predictive power.** `simulate_rolling_ic()` generates returns as `signal * k + noise`, so a positive/negative IC is baked in by construction. Separately, `run_ic_analysis()` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and cannot test predictability.

**Real IC: not yet measured.** Requires daily signal snapshots (≥30–60 trading days) paired with true forward returns.

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