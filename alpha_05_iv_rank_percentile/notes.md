# IV Rank Percentile — Alpha Signal Notes

## Hypothesis

**IV Rank Percentile (current ATM IV vs. 1-year historical range) contains predictive information for forward equity returns.**

### Rationale

1. **Mean reversion of implied volatility** — IV tends to revert to its historical mean. When IV is at historical extremes:
   - **High percentile (IV expensive, >80th)**: Options overpriced, fear elevated → mean reversion DOWN in IV → equity bounce/outperformance (sell vol premium)
   - **Low percentile (IV cheap, <20th)**: Options underpriced, complacency → mean reversion UP in IV → equity underperformance/vol expansion

2. **Cross-sectional ranking** — Ranking tickers by IV percentile:
   - Highest IV percentile → most expensive vol relative to history → potential underperformance (vol selling opportunity)
   - Lowest IV percentile → cheapest vol relative to history → potential outperformance (vol buying opportunity)

3. **IV Rank vs IV Percentile distinction**:
   - **IV Rank** = (Current IV - 52wk Low) / (52wk High - 52wk Low) — sensitive to outliers
   - **IV Percentile** = % of days in lookback where IV was below current — more robust, non-parametric

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `iv_percentile` | `% of historical days with IV ≤ current IV` | 0-100, higher = more expensive |
| `iv_zscore` | `(current_IV - hist_mean) / hist_std` | Standard deviations from mean |
| `iv_rank` | `(current - min) / (max - min)` | 0-1, sensitive to outliers |

## Expected Behavior

| Regime | IV Percentile | Expected Forward Return | Vol Trade |
|--------|---------------|------------------------|-----------|
| Fear / Stress | > 80th pctl | Mean reversion UP (short-term) | Sell vol (short straddle/strangle) |
| Complacency | < 20th pctl | Mean reversion DOWN / vol expansion | Buy vol (long straddle/strangle) |
| Normal | 40-60 pctl | No edge | Neutral |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: 14-60 DTE (near-term, liquid)
- **Lookback**: 252 trading days (~1 year) for percentile computation
- **Strikes**: Near-ATM (±5% moneyness), liquidity-weighted IV

## Implementation Notes

### Historical Data Building

Since yfinance doesn't provide historical option chains, this signal **requires daily snapshots** to build the 1-year lookback:

1. Run `main.py` daily via cron (after market close)
2. Each run appends today's ATM IV to `data/iv_history.json`
3. After ~60 days: sufficient for initial percentile calculation
4. After 252 days: full 1-year lookback established

### Approximation Method

ATM IV is computed as liquidity-weighted average of near-ATM options (±5% moneyness):
- Filters: volume > 10 OR openInterest > 100
- IV > 1% (filters zero-bid/ask)
- Weight = volume + openInterest

This avoids single-strike noise and captures the "smile" around ATM.

### Known Limitations

1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **252-day lookback** takes ~1 year to fully populate
3. **Liquidity filter** may exclude informative illiquid strikes
4. **Single expiration per day** — term structure effects not captured
5. **Earnings/events** can cause temporary IV spikes not mean-reverting

## Results (2026-09-30 — Initial Run)

| Ticker | Price | ATM IV | IV Pctile | Z-Score | Hist Range | Obs | Signal |
|--------|-------|--------|-----------|---------|------------|-----|--------|
| AAPL   | 329.40 | 0.0156 | N/A | N/A | N/A | 1 | ⏳ Building history... |
| SPY    | 764.20 | 0.0156 | N/A | N/A | N/A | 1 | ⏳ Building history... |
| QQQ    | 737.93 | 0.0156 | N/A | N/A | N/A | 1 | ⏳ Building history... |
| MSFT   | 508.96 | 0.0156 | N/A | N/A | N/A | 1 | ⏳ Building history... |
| GOOGL  | 340.92 | 0.0156 | N/A | N/A | N/A | 1 | ⏳ Building history... |
| AMZN   | 246.67 | 0.0156 | N/A | N/A | N/A | 1 | ⏳ Building history... |

**Observations:**
- First run — all tickers have only 1 observation (today)
- Percentile/Z-score will be NaN until ≥10 observations accumulated
- After ~30 days: initial percentiles become meaningful
- After ~60 days: robust enough for IC testing

## IC Analysis (Simulated)

With synthetic data (60 days, mean-reverting IV percentile vs forward returns):
- Rolling IC mean: ~ -0.18 (negative = high IV% → negative returns)
- Information Ratio: ~ -1.2
- Win rate: ~ 58% (for mean-reversion direction)
- Half-life: ~ 15 days

**Real IC pending historical data collection (need ≥30 daily snapshots).**

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate IV time series
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Test multiple horizons** — 1-day, 5-day, 10-day, 20-day forward returns
4. **Combine with other signals** — Multi-factor: IV percentile + IV skew + term structure + VRP
5. **Event adjustment** — Flag earnings/FOMC dates where IV spikes are fundamental, not mean-reverting

## Files

- `main.py` — Signal computation, outputs `data/iv_rank_percentile_latest.csv`, appends to `data/iv_history.json`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "IV Rank vs IV Percentile" — Tastytrade / Tom Sosnoff methodology
- "Volatility Mean Reversion" — Bessembinder (1994)
- "The Volatility Risk Premium" — Carr & Wu (2009)
- CBOE VIX methodology (percentile-based signals)
- "Option-Implied Volatility and Expected Returns" — Bali & Hovakimian (2009)