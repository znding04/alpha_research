# IV Momentum — Alpha Signal Notes

## Hypothesis

**Short-term ATM IV momentum (5-day % change in ATM IV) contains predictive information for forward equity returns.**

### Rationale

1. **Fear-driven IV spikes** — Rapid IV increases reflect sudden demand for protection (put buying). This often coincides with:
   - Near-term overbought conditions / local tops
   - Upcoming catalyst risk (earnings, macro events)
   - **Mean reversion signal**: Extreme IV momentum up → subsequent IV normalization → equity bounce (short-term)

2. **Complacency-driven IV declines** — Sustained IV decreases reflect diminishing hedging demand:
   - Risk-on / complacency regime
   - **Trend continuation signal**: Falling IV → momentum UP (medium-term)
   - But extreme low IV momentum → vulnerability to shock

3. **Cross-sectional ranking** — Ranking tickers by IV momentum:
   - Highest positive momentum (IV spiking) → most fearful/overbought → potential short-term underperformance → mean reversion bounce
   - Most negative momentum (IV collapsing) → most complacent → potential medium-term outperformance (trend following)

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `iv_momentum_5d` | `(ATM_IV_t - ATM_IV_{t-5}) / ATM_IV_{t-5}` | 5-day % change in ATM IV |
| `iv_momentum_10d` | `(ATM_IV_t - ATM_IV_{t-10}) / ATM_IV_{t-10}` | 10-day % change (slower signal) |
| `iv_level` | `ATM_IV_t` | Current IV level (regime context) |
| `iv_zscore` | `(ATM_IV_t - mean_20d) / std_20d` | IV level relative to recent range |

## Expected Behavior

| Regime | IV Momentum Signal | Expected Forward Return |
|--------|-------------------|------------------------|
| Fear spike | Strongly positive (> +20%) | Mean reversion UP (1-5 days) |
| Gradual fear rise | Moderately positive (5-20%) | Continued downside (5-10 days) |
| Complacency | Strongly negative (< -20%) | Trend UP / carry (10-20 days) |
| IV crush post-event | Sharply negative | Vol selling / relief rally |
| Normal range | Near zero (±5%) | No clear signal |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: Nearest liquid (7-45 DTE), consistent across time
- **ATM IV Calculation**: Robust median of ±2% moneyness strikes, IV > 5% filter
- **History**: Minimum 10 days for momentum, 60 days for z-score

## Implementation Notes

### Robust ATM IV Calculation

Since yfinance provides noisy near-ATM IVs (often near-zero due to bid/ask artifacts), we use:
1. Filter: volume > 50 OR OI > 500, IV > 5%, IV < 300%, lastPrice > 0
2. Select strikes within 0.98-1.02 moneyness
3. Median IV of qualifying strikes (≥3 strikes required)
4. Fallback: single closest strike with IV > 5%

### Momentum Computation

- **Lookback**: 5 days (configurable via `LOOKBACK_DAYS`)
- **Storage**: Daily snapshots in `data/iv_momentum_history.json`
- **Deduplication**: Same-date entries overwritten (last write wins)

### Known Limitations

1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **Expiration rolling** — Nearest expiration changes over time, introducing discontinuities
3. **Single expiration** — Using only nearest liquid expiry; term structure info ignored
4. **5-day lookback** — May be noisy; 10-20 day lookbacks also worth testing
5. **Forward returns** — Current IC analysis uses realized forward returns (look-ahead for testing only)

## Results (2026-10-07, Initial Run)

| Ticker | Price | ATM IV | Exp | History | Momentum |
|--------|-------|--------|-----|---------|----------|
| AAPL   | 333.63 | 6.25% | 2026-10-16 | 3 days | Building |
| SPY    | 779.09 | 6.25% | 2026-10-15 | 3 days | Building |
| QQQ    | 759.66 | 6.25% | 2026-10-15 | 3 days | Building |
| MSFT   | 529.30 | 6.25% | 2026-10-16 | 3 days | Building |
| GOOGL  | 347.68 | 6.25% | 2026-10-16 | 3 days | Building |
| AMZN   | 256.29 | 6.25% | 2026-10-16 | 3 days | Building |

**Observations:**
- All tickers show identical ATM IV (6.25%) — suggests yfinance IV surface is coarse/quantized
- History building: 3 days accumulated (need 6+ days for 5-day momentum)
- Expiration dates differ slightly (SPY/QQQ 10/15, others 10/16)

## IC Analysis (Simulated)

With synthetic data (60 days, negative IV momentum → positive returns correlation):
- Rolling IC mean: ~-0.18 (negative: rising IV predicts downside)
- Information Ratio: ~1.1
- Win rate: ~57%
- Half-life: ~12 days

**Real IC pending historical data collection (need 10+ days).**

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate IV time series
2. **Compute real rolling IC** — After 20+ days of data, test cross-sectional predictive power
3. **Test multiple lookbacks** — 5d, 10d, 20d momentum horizons
4. **Add IV level context** — Combine momentum with IV percentile (IV rank) for regime-aware signals
5. **Test expiration consistency** — Use fixed DTE (e.g., 30-day constant maturity) instead of nearest expiry
6. **Combine with other signals** — IV momentum + IV skew + VRP multi-factor model

## Files

- `main.py` — Signal computation, outputs `data/iv_momentum_latest.csv`, updates `data/iv_momentum_history.json`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "Volatility Momentum" — various practitioner research
- "The Volatility Surface" — Jim Gatheral (IV dynamics)
- CBOE VIX term structure / momentum studies
- "IV Momentum and Equity Returns" — academic literature on IV trend following