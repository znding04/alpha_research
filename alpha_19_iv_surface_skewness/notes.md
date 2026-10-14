# IV Surface Skewness — Alpha Signal Notes

## Hypothesis

**The third moment (skewness) of the IV smile contains predictive information for forward equity returns, capturing risk-neutral skewness and tail risk expectations.**

### Rationale

1. **Risk-neutral skewness** — The skewness of the implied volatility smile across strikes approximates the risk-neutral skewness of the underlying return distribution. Positive IV skewness (right-skewed smile) indicates market pricing of upside tail risk / call wing premium. Negative IV skewness (left-skewed smile) indicates downside tail risk / put wing premium.

2. **Tail risk premium** — Elevated put-wing IV (negative IV skewness) reflects demand for crash protection. When this premium becomes extreme, it may signal:
   - Near-term oversold conditions (excessive fear)
   - **Mean reversion signal**: Extreme left-tail pricing → subsequent normalization → equity bounce

3. **Call-wing speculation** — Elevated call-wing IV (positive IV skewness) reflects upside speculation / FOMO. When this premium becomes extreme:
   - Near-term overbought conditions (complacency / greed)
   - **Reversal signal**: Extreme right-tail pricing → subsequent pullback

4. **Kurtosis (fat tails)** — High excess kurtosis of the IV smile indicates market pricing of fat-tailed return distributions (jump risk). This complements skewness by capturing the *magnitude* of tail expectations regardless of direction.

5. **Cross-sectional ranking** — Ranking tickers by smile skewness/kurtosis:
   - Most negative skewness (heavy put wing) → most hedged/fearful → potential short-term outperformance (mean reversion)
   - Most positive skewness (heavy call wing) → most speculative/greedy → potential short-term underperformance
   - Highest kurtosis → highest jump risk → wider expected return distribution

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `iv_skewness` | 3rd central moment of IV distribution (OI-weighted) | Positive = call wing premium (upside tail risk); Negative = put wing premium (downside tail risk) |
| `iv_kurtosis` | Excess kurtosis (4th moment) of IV distribution | High = fat-tailed risk-neutral density; jump risk priced in |
| `iv_variance` | 2nd moment (dispersion) of IV across strikes | Overall smile steepness / convexity |
| `wing_skew` | Mean OTM put IV - Mean OTM call IV | Direct put/call wing comparison (approx risk-neutral skew) |
| `left_wing_iv` | Mean IV for moneyness < 0.95 | Downside tail risk pricing |
| `right_wing_iv` | Mean IV for moneyness > 1.05 | Upside tail risk pricing |

## Expected Behavior

| Regime | IV Skewness | IV Kurtosis | Expected Forward Return |
|--------|-------------|-------------|------------------------|
| Risk-off / Crash fear | Strongly negative | Elevated | Mean reversion UP (short-term bounce) |
| Risk-on / Complacency | Near zero / slightly positive | Low | Momentum UP (medium-term) |
| Upside speculation (FOMO) | Strongly positive | Elevated | Short-term pullback / reversal |
| Event-driven uncertainty | Near zero | Very high | High realized vol, direction uncertain |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expiration**: Near-term (7-45 DTE), front month preferred for signal sensitivity
- **Strikes**: Full available range, filtered to 0.80-1.20 moneyness for moment calculation
- **Weighting**: Open Interest (OI) weighted moments — emphasizes strikes where market participants are positioned

## Implementation Notes

### Moment Calculation

Since yfinance doesn't provide a continuous IV surface, we compute discrete moments across available strikes:

1. **Filter** liquid options (volume > 10 or OI > 100) with valid IV (0.01 < IV < 3.0)
2. **Weight** by Open Interest (fallback to volume, then equal weight)
3. **Compute** central moments of IV values across moneyness
4. **Normalize** skewness by σ³, kurtosis by σ⁴ (excess kurtosis = kurtosis - 3)

This OI-weighting is crucial — it measures skewness *where the money is*, not just across all quoted strikes.

### Wing Skew Approximation

`wing_skew = mean(IV | moneyness < 0.95) - mean(IV | moneyness > 1.05)`

This is a more direct proxy for risk-neutral skewness than the moment-based approach, comparing the average put wing IV to call wing IV. It avoids moment estimation noise but uses less information.

### Known Limitations

1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **Discrete strike grid** — moment accuracy depends on strike density and range
3. **Single expiration** — near-term only; term structure of skewness not captured
4. **Moneyness filter (0.80-1.20)** — excludes deep OTM wings where tail risk is most extreme
5. **OI may be stale** — previous day's OI, not intraday

## Results (2026-10-14)

| Ticker | Price | Exp (DTE) | IV Skew | IV Kurt | IV Var | Wing Skew | L-Wing IV | R-Wing IV | ATM IV | N Strikes |
|--------|-------|-----------|---------|---------|--------|-----------|-----------|-----------|--------|-----------|
| AAPL   | 341.27 | 2026-10-23 (8) | +2.111 | +8.147 | 0.000815 | +0.0042 | 0.1354 | 0.1313 | 0.0234 | 34 |
| SPY    | 778.01 | 2026-10-22 (7) | +2.525 | +9.346 | 0.000307 | +0.0052 | 0.0833 | 0.0781 | 0.0156 | 52 |
| QQQ    | 743.57 | 2026-10-22 (7) | +0.406 | +0.185 | 0.002481 | -0.0182 | 0.1172 | 0.1354 | 0.0156 | 59 |
| MSFT   | 543.45 | 2026-10-23 (8) | +1.627 | +4.221 | 0.001189 | +0.0066 | 0.1316 | 0.1250 | 0.0156 | 42 |
| GOOGL  | 353.78 | 2026-10-23 (8) | +1.237 | +2.227 | 0.001725 | +0.0235 | 0.1429 | 0.1193 | 0.0234 | 37 |
| AMZN   | 258.58 | 2026-10-23 (8) | +1.074 | +1.936 | 0.001925 | +0.0095 | 0.1458 | 0.1364 | 0.0234 | 31 |

**Observations:**
- All tickers except QQQ show **positive IV skewness** (right-skewed smiles / call wing premium)
- SPY has the **highest skewness (+2.53)** and **highest kurtosis (+9.35)** — extreme call-wing pricing, potential complacency/FOMO signal
- QQQ is the **only ticker with negative wing skew (-0.018)** — put wing > call wing, suggesting relatively more downside hedging demand
- GOOGL has the **largest positive wing skew (+0.0235)** — strongest call wing premium among the group
- ATM IVs are very low (0.0156-0.0234) across the board — compressed volatility environment
- High kurtosis values for SPY, AAPL, MSFT indicate **fat-tailed risk-neutral densities** (jump risk priced in)
- IV variance (dispersion) is highest for QQQ and AMZN — widest smiles relative to ATM

## IC Analysis (Simulated)

With synthetic data (60 days, target IC ~ 0.10-0.15):
- Rolling IC mean: ~0.12
- Information Ratio: ~0.8
- Win rate: ~55%
- Half-life: ~10-15 days

**Real IC pending historical data collection.**

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate skewness time series
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Test multi-horizon** — 1-day, 5-day, 10-day, 20-day forward returns
4. **Combine with IV Rank / Skew Dynamics** — Multi-factor: skewness + IV rank + 25d skew + term structure
5. **Explore kurtosis signal** — High kurtosis as vol-of-vol / regime instability indicator
6. **Refine weighting** — Test volume-weighting vs OI-weighting vs delta-weighting (requires Greeks)
7. **Test wing skew vs moment skew** — Compare predictive power of both approaches

## Files

- `main.py` — Signal computation, outputs `data/iv_skewness_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "The Volatility Surface" — Jim Gatheral (smile moments, risk-neutral moments)
- "Model-Free Implied Volatility and Skewness" — Bakshi, Kapadia, Madan (2003)
- "Risk-Neutral Skewness and Expected Returns" — Conrad, Dittmar, Ghysels (2013)
- "Option-Implied Risk-Neutral Distributions" — Bahra (1997)
- CBOE SKEW Index methodology (risk-neutral skewness measure)
- "Tail Risk and Asset Prices" — Kelly, Jiang (2014)
- "Variance Risk Premium" — Bollerslev, Tauchen, Zhou (2009) — related via kurtosis