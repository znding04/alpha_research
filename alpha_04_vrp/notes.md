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

## Results (2026-10-16 close, run 2026-10-18)

| Ticker | Price | ATM IV | Realized Vol (30d) | VRP (IV²-RV²) | VRP (vol pts) | VRP Ratio (IV²/RV²) |
|--------|-------|--------|--------------------|---------------|---------------|---------------------|
| AAPL   | 343.46 | 0.3192 | 0.1978 | +0.0627 | 0.2505 | 2.60 |
| SPY    | 763.25 | 0.1547 | 0.1015 | +0.0136 | 0.1167 | 2.32 |
| QQQ    | 709.80 | 0.2411 | 0.1680 | +0.0299 | 0.1728 | 2.06 |
| MSFT   | 529.05 | 0.3725 | 0.2222 | +0.0894 | 0.2990 | 2.81 |
| GOOGL  | 340.59 | 0.4328 | 0.2353 | +0.1320 | 0.3633 | 3.38 |
| AMZN   | 250.00 | 0.4751 | 0.2357 | +0.1701 | 0.4125 | 4.06 |

Raw: `data/vrp_latest.csv`. The 2026-09-29 table (ATM IV = 0.0156 placeholders, no RV) was discarded.

**Observations:**
- VRP is positive for every name (IV > RV), as expected for the variance risk premium.
- Cross-sectional ranking: AMZN > GOOGL > MSFT > AAPL > QQQ > SPY.
- **Earnings contamination:** the ATM IV comes from the nearest expiration in 14–60 DTE, which for AMZN/GOOGL/MSFT/AAPL straddles their late-October earnings. Their elevated VRP largely reflects the earnings event premium, not a steady-state VRP. The index ETFs (SPY, QQQ) are the cleanest readings. Fix: skip expirations that contain an earnings date, or use a fixed 30d interpolated IV ex-event.

## IC Analysis (Simulated)

With synthetic data (60 days, positive correlation between VRP and returns):
- Rolling IC mean: ~0.15-0.20
- Information Ratio: ~1.0-1.5
- Win rate: ~55-60%
- Half-life: ~10-15 days

**Interpretation**: Positive IC expected (earning the variance risk premium).

**⚠️ These are synthetic demo numbers, not evidence of predictive power.** `simulate_rolling_ic()` generates returns as `signal * k + noise`, so a positive/negative IC is baked in by construction. Separately, `run_ic_analysis()` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and cannot test predictability.

**Real IC: not yet measured.** Requires daily signal snapshots (≥30–60 trading days) paired with true forward returns.

## Next Steps

1. ~~**Fix ATM IV values**~~ — Resolved: 2026-10-16 run gives sensible ATM IVs (0.15–0.48). The 0.0156 values were yfinance placeholders. Remaining issue: earnings-event contamination (see Observations).

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