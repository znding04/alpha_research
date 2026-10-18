# VRP Carry / Roll-down — Alpha Signal Notes

## Hypothesis

**VRP term structure carry (near-term VRP minus far-term VRP) and roll-down (daily VRP decay as options approach expiry) contain predictive information for forward equity returns.**

### Rationale

1. **Variance Risk Premium (VRP) Term Structure** — VRP = IV² - RV² typically exhibits a term structure:
   - **Contango (normal)**: Near-term VRP < Far-term VRP (positive slope) — insurance premium increases with horizon
   - **Backwardation (inverted)**: Near-term VRP > Far-term VRP (negative slope) — acute near-term fear, steep premium for short-dated protection

2. **Carry Signal** — `VRP_carry = VRP_near - VRP_far`:
   - **Positive carry** (near > far, backwardation): Market pricing excessive near-term fear. Rolling short VRP (selling near-term vol, buying far-term) earns positive carry as term structure normalizes. **Predicts mean reversion UP** in equities.
   - **Negative carry** (near < far, contango): Normal term structure. Carry trade loses money (paying roll cost). **Less predictive** or predicts trend continuation.

3. **Roll-down Signal** — Daily VRP decay as DTE decreases:
   - Options lose time value; VRP typically decays toward expiry (especially in contango)
   - `roll_down_daily = -d(VRP)/d(DTE)` ≈ term structure slope (VRP per day)
   - High roll-down = steep VRP decay = expensive near-term protection relative to far-term
   - **High roll-down → subsequent VRP compression → equity bounce**

4. **Cross-sectional Ranking** — Ranking tickers by carry/roll-down:
   - Highest carry/roll-down → most over-hedged near-term → potential short-term outperformance
   - Lowest carry/roll-down → complacent / normal term structure → less signal

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `vrp_carry` | `VRP_near - VRP_far` | Positive = backwardation (near-term fear premium) |
| `vrp_slope_per_day` | `(VRP_far - VRP_near) / (DTE_far - DTE_near)` | VRP term structure slope |
| `roll_down_daily` | `-vrp_slope_per_day` | Positive = VRP decays as DTE decreases |
| `carry_ratio` | `vrp_carry / VRP_near` | Carry per unit of near-term VRP (normalized) |
| `near_vrp` | `IV_near² - RV²` | Near-term variance risk premium level |

Where:
- `VRP = IV² - RV²` (variance space, not vol space)
- `IV` = ATM implied volatility for given expiration
- `RV` = 20-day realized volatility (annualized)

## Expected Behavior

| Regime | VRP Term Structure | Carry Signal | Expected Forward Return |
|--------|-------------------|--------------|------------------------|
| Risk-off / Fear spike | Inverted (backwardation) | **High positive** | Mean reversion UP (1-5 days) |
| Risk-on / Complacency | Normal contango | Low/negative | Trend continuation |
| Earnings / Event risk | Inverted near-term | **High positive** | Post-event normalization UP |
| Vol crush aftermath | Steep contango | Negative | Drift / mean reversion DOWN |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: 5-180 DTE, focus on nearest 2-3 liquid expiries
- **Realized Vol**: 20-day rolling (annualized)
- **IV**: ATM implied vol per expiration

## Implementation Notes

### VRP in Variance Space
VRP is computed in **variance space** (IV² - RV²), not vol space (IV - RV), because:
- Variances are additive; vols are not
- VRP in vol space understates premium when IV and RV are both high
- Theoretical foundation: VRP = E[RV²] - E[IV²] under risk-neutral vs physical measure

### Approximation Method
- ATM IV per expiration: strike closest to current spot
- Realized vol: 20-day trailing daily close-to-close returns, annualized (×√252)
- Minimum DTE filter: 5 days (excludes noisy weeklies)

### Known Limitations
1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **Single snapshot** — cannot compute `Δcarry_1d` or rolling IC without history
3. **RV window sensitivity** — 20-day RV may lag regime changes; alternative: 10-day or EWMA
4. **IV smoothing** — ATM IV per expiration has noise; could fit parametric surface (SVI)
5. **Liquidity filter** may exclude informative illiquid expiries

## Results (2026-10-16 close)

*Run 2026-10-18 on Friday's closing chains. RV = 20-day close-to-close, annualized.*

| Ticker | Price | RV(20d) | Near DTE | Far DTE | Near IV | Far IV | Near VRP | Far VRP | VRP Carry | Roll-down/day | Carry Ratio |
|--------|-------|---------|----------|---------|---------|--------|----------|---------|-----------|---------------|-------------|
| AAPL   | 343.46 | 0.1620 | 7 | 179 | 0.2726 | 0.3130 | 0.0481 | 0.0717 | -0.0237 | -0.000138 | -0.492 |
| SPY    | 763.25 | 0.1047 | 7 | 163 | 0.1394 | 0.1894 | 0.0085 | 0.0249 | -0.0165 | -0.000106 | -1.944 |
| QQQ    | 709.80 | 0.1856 | 7 | 163 | 0.2278 | 0.2587 | 0.0175 | 0.0325 | -0.0151 | -0.000097 | -0.863 |
| MSFT   | 529.05 | 0.2234 | 7 | 179 | 0.2884 | 0.3400 | 0.0333 | 0.0657 | -0.0324 | -0.000189 | -0.975 |
| GOOGL  | 340.59 | 0.2263 | 7 | 179 | 0.3261 | 0.4003 | 0.0551 | 0.1090 | -0.0540 | -0.000314 | -0.979 |
| AMZN   | 250.00 | 0.2439 | 7 | 179 | 0.3065 | 0.4128 | 0.0345 | 0.1109 | -0.0765 | -0.000445 | -2.219 |

**Observations:**
- **Data issue resolved for this run** — IVs are real and differ across expirations (near 0.14-0.33, far 0.19-0.41). The earlier 0.0156 values were yfinance placeholders. The placeholder problem can recur (it hit the 2026-10-05 run), so outputs still need an IV sanity check before use.
- **VRP positive everywhere** (IV > RV at both tenors), unlike the 2026-10-05 table, whose negative VRPs came from placeholder IVs.
- **All six names in contango** (negative carry): no backwardation / near-term fear signal today.
- AMZN has the steepest VRP term structure (carry -0.077), QQQ the flattest (-0.015).
- **Carry ratio is unstable** when near VRP is small: SPY (-1.94) and AMZN (-2.22) are large mostly because their near VRP is small.
- Single snapshot: `Δcarry_1d` and real IC need accumulated history.

*2026-10-05 results removed: every IV was the 0.0156 placeholder, so all VRP/carry values were invalid.*

## IC Analysis

**Real IC: not yet measurable.** A real forward IC needs a daily snapshot history of this signal (≥30-60 trading days), each snapshot paired with returns realized *after* it. The current `ic_analysis.py` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and is not evidence of predictive power.

**Synthetic demo only (not evidence):** the figures below come from `simulate_rolling_ic()`, which generates random data with a signal/return correlation built in. They show what the code reports when that assumption holds, nothing about this signal.

- Rolling IC mean: ~0.20
- Information Ratio: ~1.3
- Win rate: ~58%
- Half-life: ~12 days

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate VRP carry time series
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Test carry change signal** — `Δcarry_1d` vs 1-5 day forward returns
4. **Combine with IV Rank (alpha_01)** — Multi-factor: VRP carry + IV rank + skew (alpha_02)
5. **Test RV window sensitivity** — 10d, 20d, 60d realized vol; EWMA
6. **Surface fitting** — Fit SVI or polynomial to IV surface for smoother VRP term structure

## Files

- `main.py` — Signal computation, outputs `data/vrp_carry_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "Variance Risk Premium" — Bollerslev, Tauchen, Zhou (2009)
- "The Term Structure of Variance Risk Premia" — Dew-Becker et al. (2017)
- "Carry Trades in Volatility Space" — CBOE / Volatility Research
- "Roll-Down and Carry in Volatility Markets" — JPMorgan / Goldman quant research
- CBOE VIX Term Structure methodology