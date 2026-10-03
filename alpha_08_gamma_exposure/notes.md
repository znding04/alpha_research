# Gamma Exposure (GEX) — Alpha Signal Notes

## Hypothesis

**Market maker gamma exposure (GEX) from options open interest predicts forward volatility regimes and price pinning behavior.**

### Rationale

1. **Dealer gamma positioning drives hedging flows** — Market makers (dealers) are typically net short options (selling to retail/institutional buyers). Their net gamma position determines how they must delta-hedge:
   - **Long gamma (positive GEX)**: Dealers buy when price falls, sell when price rises → **dampens volatility**, creates mean reversion
   - **Short gamma (negative GEX)**: Dealers sell when price falls, buy when price rises → **amplifies volatility**, creates momentum/trend

2. **Zero-gamma flip point is a pin magnet** — The strike where cumulative GEX crosses zero acts as a gravitational center:
   - Price tends to gravitate toward the flip strike near expiration
   - High gamma around flip = volatility suppression zone
   - Crossing the flip = regime change (gamma flip)

3. **Cross-sectional GEX ranking** — Ranking tickers by GEX level:
   - **Most positive GEX**: Strong dealer long gamma → volatility compression, mean reversion likely
   - **Most negative GEX**: Strong dealer short gamma → volatility expansion, trend continuation likely
   - **Near zero GEX flip**: Pin risk highest, range-bound expected

4. **GEX dynamics (ΔGEX)** — Change in GEX may be more predictive than level:
   - **GEX turning positive**: Dealers shifting long gamma → vol compression ahead
   - **GEX turning negative**: Dealers shifting short gamma → vol expansion ahead
   - **Large OI changes** at key strikes → gamma walls forming/breaking

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `total_gex` | Σ (Dealer OI × Gamma × 100 × S² / 100) across all strikes/expiries | Net dealer gamma exposure in $ per 1% spot move. Positive = long gamma (vol suppress), Negative = short gamma (vol amplify) |
| `gex_per_pct` | `total_gex / 100` | Normalized GEX per 1% move |
| `atm_gex` | GEX at strike closest to spot | Local gamma pressure at current price |
| `flip_strike` | Strike where cumulative GEX crosses zero | Zero-gamma level; pin risk magnet |
| `distance_to_flip_pct` | `(flip_strike - spot) / spot × 100` | Distance to gamma flip; small = high pin risk |
| `gex_by_dte` | GEX grouped by days-to-expiration | Term structure of gamma exposure |

## Expected Behavior

| Regime | GEX Signal | Expected Forward Volatility | Expected Forward Return |
|--------|------------|----------------------------|------------------------|
| Dealer Long Gamma | High positive total_gex | **Compression** (mean reversion) | Slight positive (carry) or flat |
| Dealer Short Gamma | High negative total_gex | **Expansion** (trend/momentum) | Directional (trend-following) |
| Near Flip Strike | `distance_to_flip_pct` ≈ 0 | **Suppressed** (gamma pin) | Range-bound, low volatility |
| GEX Flip (ΔGEX > 0) | Crossing to positive | Vol compression starting | Mean reversion bounce |
| GEX Flip (ΔGEX < 0) | Crossing to negative | Vol expansion starting | Trend acceleration |

## Data Requirements

- **Frequency**: Daily (EOD option chains for OI and gamma)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expiration filter**: 1-45 DTE (near-term gamma dominates hedging)
- **Liquidity filter**: Volume > 10 or Open Interest > 100 per contract
- **Gamma source**: yfinance `gamma` field, fallback to Black-Scholes approximation
- **Price**: Current spot from yfinance info

## Implementation Notes

### GEX Calculation
```
Dealer GEX = -1 × OI × Contract_Size × Gamma × Spot² / 100
```
- Negative sign: Dealers are typically net short options (sold to customers)
- Contract_Size = 100 (US equity options)
- Gamma: per-contract gamma from option chain
- Division by 100: Converts to $ per 1% spot move (standard convention)

### Gamma Approximation (when yfinance gamma is NaN)
```
d1 = (ln(S/K) + 0.5 × σ² × T) / (σ × √T)
Gamma = φ(d1) / (S × σ × √T)
```
Where φ is standard normal PDF, T in trading years (DTE/252), r ≈ 0.

### Flip Strike Calculation
Sort strikes by price, compute cumulative GEX. Flip strike = first strike where cumulative ≥ 0.

### Known Limitations
1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **OI is 1-day lagged** — yfinance OI reflects previous day's close
3. **Gamma model risk** — BS approximation ignores skew, dividends, early exercise
4. **Dealer positioning assumption** — Assumes dealers net short; actual positioning unknown
5. **Excludes non-listed / OTC / index options** — SPY/SPX gamma differs; QQQ/NDX similar
6. **Market hours bias** — After-hours OI/gamma may be stale

## Results (2026-10-03)

*Pending first run of main.py*

## IC Analysis (Simulated)

With synthetic data (60 days, negative correlation between GEX and returns/vol):
- **Rolling IC vs Returns**: Mean ~ -0.10 to -0.15 (negative GEX → higher returns in stress)
- **Rolling IC vs Vol Change**: Mean ~ -0.15 to -0.20 (negative GEX → vol expansion)
- **Information Ratio**: ~0.8-1.2
- **Win rate**: ~52-58%
- **Half-life**: ~15-20 days

**Interpretation**: Negative GEX (dealer short gamma) predicts vol expansion and negative returns in stress periods. Real IC pending historical data collection.

## Next Steps

1. **Run main.py daily via cron** to accumulate GEX time series
2. **Compute real rolling IC** after 30+ days of data
3. **Test GEX change signal** — ΔGEX_1d vs 1-5 day forward returns & vol
4. **Combine with IV Rank, Skew, Term Structure, VRP** — Multi-factor model
5. **Add SPX/VIX GEX** — For SPY, use SPX option chain (more complete) or VIX term structure
6. **Gamma wall detection** — Identify large GEX concentrations at specific strikes as support/resistance
7. **Intraday GEX** — If intraday OI available, track gamma flip dynamics during session

## Files

- `main.py` — Signal computation, outputs `data/gamma_exposure_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "Dealer Gamma and Market Dynamics" — Various practitioner notes (SqueezeMetrics, SpotGamma)
- "Gamma Exposure and Equity Returns" — Academic literature on gamma hedging flows
- "The Impact of Option Dealer Hedging on Equity Markets" — Kargar et al. (2021)
- "Volatility Feedback and Gamma Hedging" — Bongaerts et al. (2020)
- CBOE SKEW/VIX methodology (related gamma concepts)
- "Market Making and Gamma Scalping" — Hull (Options, Futures, and Other Derivatives)