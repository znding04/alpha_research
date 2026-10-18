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

## Results — expanded ETF universe (2026-10-16 close)

Universe: 12 ETFs (SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO) + AAPL, MSFT, GOOGL, AMZN, from `common/universe.py`. Raw: `data/snapshots/2026-10-16/`.

| ticker | dte | atm_iv | iv_skewness | iv_kurtosis | wing_skew |
|---|---|---|---|---|---|
| SPY | 7 | 0.1328 | 2.3403 | 8.7567 | 0.2140 |
| QQQ | 7 | 0.2235 | 2.6083 | 6.1912 | 0.2454 |
| IWM | 7 | 0.1806 | 1.6257 | 2.5230 | 0.1319 |
| DIA | 11 | 0.1520 | 2.0121 | 3.4789 | 0.1689 |
| GLD | 7 | 0.1878 | 1.2903 | 1.9886 | 0.0171 |
| SLV | 7 | 0.3291 | 2.3966 | 8.4543 | 0.0861 |
| TLT | 7 | 0.1377 | 0.9803 | -0.2064 | -0.0296 |
| EEM | 11 | 0.2935 | 0.3126 | -1.7445 | 0.0377 |
| EWZ | 11 | 0.8386 | -1.6575 | 2.8114 | 0.3950 |
| FXI | 11 | 0.3164 | -0.3277 | -0.9747 | -0.5908 |
| GDX | 11 | 0.4663 | 2.3793 | 8.0915 | -0.0231 |
| USO | 9 | 0.4962 | 1.5690 | 13.6 | 0.0257 |
| AAPL | 7 | 0.2650 | 5.0522 | 36.5 | 0.2290 |
| MSFT | 7 | 0.2746 | 1.5172 | 0.7566 | 0.1048 |
| GOOGL | 7 | 0.3340 | 3.2159 | 15.0 | 0.1534 |
| AMZN | 7 | 0.3508 | 1.3352 | 0.8408 | 0.1556 |

**ETF vs single-name observations:**
- Equity ETFs and SLV/GDX have strongly positive IV skewness (put wing rich); EWZ, FXI and EEM are negative/near zero — their smiles are call-wing heavy or flat.
- AAPL (kurtosis 36.5) and GOOGL (15.0) are still outliers at 7 DTE, driven by a few far-wing strikes; expiry selection now skips expiries with <5 liquid puts/calls (fixes GDX).

## Results (2026-10-16 close)

*Run 2026-10-18 on Friday's closing chains, nearest liquid expiry 2026-10-26 (7 DTE). The 2026-10-14 table was removed because its ATM IVs (0.0156-0.0234) were yfinance placeholders, which invalidated those moments and wing IVs.*

| Ticker | Price | Exp (DTE) | IV Skew | IV Kurt | IV Var | Wing Skew | L-Wing IV | R-Wing IV | ATM IV | N Strikes |
|--------|-------|-----------|---------|---------|--------|-----------|-----------|-----------|--------|-----------|
| AAPL   | 343.46 | 2026-10-26 (7) | +5.052 | +36.487 | 0.001818 | +0.2290 | 0.4785 | 0.2494 | 0.2650 | 42 |
| SPY    | 763.25 | 2026-10-26 (7) | +2.340 | +8.757 | 0.003490 | +0.2140 | 0.3732 | 0.1592 | 0.1328 | 119 |
| QQQ    | 709.80 | 2026-10-26 (7) | +2.608 | +6.191 | 0.010563 | +0.2454 | 0.4756 | 0.2302 | 0.2235 | 126 |
| MSFT   | 529.05 | 2026-10-26 (7) | +1.517 | +0.757 | 0.009894 | +0.1048 | 0.4429 | 0.3381 | 0.2746 | 44 |
| GOOGL  | 340.59 | 2026-10-26 (7) | +3.216 | +15.044 | 0.002370 | +0.1534 | 0.5138 | 0.3604 | 0.3340 | 39 |
| AMZN   | 250.00 | 2026-10-26 (7) | +1.335 | +0.841 | 0.002335 | +0.1556 | 0.5005 | 0.3449 | 0.3508 | 27 |

**Observations:**
- **All six have a positive wing skew** (OTM put IV > OTM call IV by 0.10-0.25). This is a normal equity put skew, which reverses the earlier "call wing premium" reading that came from placeholder data.
- QQQ (+0.245) and AAPL (+0.229) have the steepest put wings. MSFT is the flattest (+0.105).
- The **moment skewness is positive for all**: the cross-strike IV distribution has a long right tail, driven by a few very high far-OTM put IVs.
- ⚠️ **AAPL kurtosis (36.5) and GOOGL kurtosis (15.0) are outliers**, likely driven by one or two far-wing strikes. At 7 DTE the moments are sensitive to strike coverage (27-126 strikes), so trimming or a vega/delta-weighted version is advisable before IC testing.

## IC Analysis

**Real IC: not yet measurable.** A real forward IC needs a daily snapshot history of this signal (≥30-60 trading days), each snapshot paired with returns realized *after* it. The current `ic_analysis.py` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and is not evidence of predictive power.

**Synthetic demo only (not evidence):** the figures below come from `simulate_rolling_ic()`, which generates random data with a signal/return correlation built in. They show what the code reports when that assumption holds, nothing about this signal.

- Rolling IC mean: ~0.12
- Information Ratio: ~0.8
- Win rate: ~55%
- Half-life: ~10-15 days

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