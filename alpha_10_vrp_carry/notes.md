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

## Results (2026-10-05)

| Ticker | Price | RV(20d) | Near DTE | Far DTE | Near IV | Far IV | Near VRP | Far VRP | VRP Carry | Roll-down/day | Carry Ratio |
|--------|-------|---------|----------|---------|---------|--------|----------|---------|-----------|---------------|-------------|
| AAPL   | 333.69 | 0.2309 | 6 | 164 | 0.0156 | 0.0156 | -0.0531 | -0.0531 | 0.0000 | -0.0000 | -0.0000 |
| SPY    | 769.64 | 0.1036 | 6 | 176 | 0.0156 | 0.0156 | -0.0105 | -0.0105 | 0.0000 | -0.0000 | -0.0000 |
| QQQ    | 749.58 | 0.1531 | 6 | 176 | 0.0156 | 0.0156 | -0.0232 | -0.0232 | 0.0000 | -0.0000 | -0.0000 |
| MSFT   | 517.53 | 0.2236 | 6 | 164 | 0.0156 | 0.0156 | -0.0498 | -0.0498 | 0.0000 | -0.0000 | -0.0000 |
| GOOGL  | 343.50 | 0.2597 | 6 | 164 | 0.0156 | 0.0156 | -0.0672 | -0.0672 | 0.0000 | -0.0000 | -0.0000 |
| AMZN   | 251.52 | 0.2137 | 6 | 164 | 0.0156 | 0.0156 | -0.0454 | -0.0454 | 0.0000 | -0.0000 | -0.0000 |

**Observations:**
- **All ATM IVs identical (0.0156)** — yfinance returns placeholder IVs; no term structure visible
- VRP varies only by realized vol (RV): GOOGL highest (-0.067), SPY lowest (-0.010)
- All VRP negative (RV > IV) — market pricing less uncertainty than recently realized
- **VRP carry = 0 for all** — flat IV term structure eliminates carry signal
- **Data quality limitation**: yfinance IV data insufficient for term structure analysis
- Need alternative IV data source (Polygon, CBOE, or broker API) for this signal to work

**Action Required**: This signal requires proper IV term structure data. With current yfinance data, the signal is non-functional. Consider:
1. Using a paid options data provider (Polygon.io, CBOE LiveVol)
2. Computing IV from mid-prices using Black-Scholes (yfinance gives lastPrice, bid, ask)
3. Focusing on signals that work with flat IV (e.g., IV Rank, VRP level vs RV)

## IC Analysis (Simulated)

With synthetic data (60 days, target IC ~ 0.15-0.25):
- Rolling IC mean: ~0.20
- Information Ratio: ~1.3
- Win rate: ~58%
- Half-life: ~12 days

**Real IC pending historical data collection.**

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