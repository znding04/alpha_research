# VRP (Variance Risk Premium) — Alpha Signal Notes

## Hypothesis

**The Variance Risk Premium (VRP = IV² - RV²) contains predictive information for forward equity returns.**

### Rationale

1. **Volatility risk premium exists** — Options are systematically priced above realized volatility (IV > RV on average). Investors pay a premium for downside protection, creating a persistent positive VRP that can be harvested.

2. **VRP as fear gauge** — Elevated VRP (IV >> RV) reflects high demand for protection / fear. This can signal:
   - **Near-term oversold**: Extreme fear → mean reversion bounce likely
   - **Premium harvesting opportunity**: High VRP = rich option prices = good time to sell vol

3. **Cross-sectional ranking** — Ranking tickers by VRP level:
   - **Highest VRP**: Options most expensive → highest expected return from selling vol / mean reversion potential
   - **Lowest/negative VRP**: Options cheap relative to realized vol → complacency, potential underperformance

4. **VRP dynamics** — Change in VRP (ΔVRP) may be more predictive than level:
   - **VRP spiking up**: Sudden fear spike → short-term reversal
   - **VRP collapsing**: Complacency setting in → trend continuation or risk buildup

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `vrp_variance` | `IV² - RV²` | Positive = options expensive (fear premium) |
| `vrp_vol_points` | `sign(VRP) × √|VRP|` | VRP in annualized vol units |
| `vrp_ratio` | `IV² / RV²` | Ratio > 1 = IV > RV (normal state) |
| `atm_iv` | ATM implied vol | Raw IV level |
| `realized_vol` | Historical vol (30d) | Raw RV level |

## Expected Behavior

| Regime | VRP Signal | Expected Forward Return |
|--------|------------|------------------------|
| Risk-off / Panic | High positive VRP | Mean reversion UP (1-5 days) |
| Risk-on / Complacent | Low/negative VRP | Momentum UP or flat |
| Normal | Moderate positive VRP | Earn volatility risk premium |
| VRP spike (ΔVRP > 0) | Sudden IV expansion | Short-term bounce |
| VRP crash (ΔVRP < 0) | Sudden IV compression | Trend continuation / risk-on |

## Data Requirements

- **Frequency**: Daily (EOD option chains for IV, daily closes for RV)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **IV source**: Nearest liquid expiration (2-60 DTE), ATM strike
- **RV calculation**: 30-day rolling realized volatility (annualized, √252)
- **Liquidity filter**: Volume > 10 or OI > 100 per leg

## Implementation Notes

### IV Calculation
- Uses nearest liquid expiration within 2-60 DTE
- ATM strike = strike closest to spot
- Average of call/put IV if both liquid, else available side

### RV Calculation
- 30 trading days of daily log returns
- Annualized: `std(log_returns) × √252`
- Uses `yfinance` history (adjusted close)

### VRP Formula
```
VRP = IV² - RV²
```
Positive VRP = variance risk premium exists (normal state).
Negative VRP = realized vol exceeded implied (rare, stress periods).

### Known Limitations
1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **Single expiration** — Using nearest expiry ignores term structure info
3. **30-day RV window** — Choice of lookback affects signal; shorter = noisier, longer = slower
4. **ATM IV only** — Doesn't capture skew/smile information
5. **Market hours bias** — Bid/ask often 0 after hours; relies on lastPrice-derived IV

## Results (2026-09-29)

| Ticker | Price | ATM IV | Realized Vol | VRP (IV²-RV²) | VRP Ratio |
|--------|-------|--------|--------------|---------------|-----------|
| AAPL   | 338.40 | 0.0156 | — | — | — |
| SPY    | 765.61 | 0.0156 | — | — | — |
| QQQ    | 736.53 | 0.0156 | — | — | — |
| MSFT   | 509.22 | 0.0156 | — | — | — |
| GOOGL  | 342.75 | 0.0313 | — | — | — |
| AMZN   | 246.15 | 0.0156 | — | — | — |

*Data pending: Running main.py to populate realized vol and VRP*

## IC Analysis (Simulated)

With synthetic data (60 days, positive correlation between VRP and returns):
- Rolling IC mean: ~0.15-0.20
- Information Ratio: ~1.0-1.5
- Win rate: ~55-60%
- Half-life: ~10-15 days

**Interpretation**: Positive IC expected (earning the variance risk premium). Real IC pending historical data collection.

## Next Steps

1. **Fix ATM IV values** — Current ATM IVs seem too low (0.0156 = 1.56%), likely picking up near-zero IV from illiquid options. Need better liquidity filtering or different strike selection.

2. **Build historical database** — Run `main.py` daily via cron to accumulate VRP time series

3. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power

4. **Test VRP change signal** — `ΔVRP_1d` vs 1-5 day forward returns

5. **Combine with IV Rank & Skew & Term Structure** — Multi-factor: VRP + IV rank + skew + term slope

6. **Add VIX VRP** — For SPY, compute VRP using VIX (30d IV) vs SPX realized vol as benchmark

## Files

- `main.py` — Signal computation, outputs `data/vrp_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "Variance Risk Premium" — Bollerslev, Tauchen, Zhou (2009)
- "The Variance Risk Premium and Expected Returns" — Carr, Wu (2009)
- "Expected Returns and the Variance Risk Premium" — Bekaert, Hoerova (2014)
- CBOE VIX methodology (model-free implied variance)
- "Volatility Risk Premiums" — Dew-Becker et al. (2017)