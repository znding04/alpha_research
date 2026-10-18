# IV Skew Convexity (Butterfly Skew) — Alpha Signal Notes

## Hypothesis

**The convexity/curvature of the put-call IV skew across moneyness contains predictive information for forward equity returns beyond linear skew.**

### Rationale

1. **Linear skew vs. convexity** — Standard 25-delta skew (put_25d_IV - call_25d_IV) measures the *slope* of the skew. Convexity measures the *curvature* — whether tail options (10-delta, 5-delta) are priced richer/cheaper than a linear extrapolation from ATM would predict.

2. **Tail risk pricing** — High positive convexity means deep OTM puts and calls are both expensive relative to ATM and 25-delta. This indicates:
   - Market pricing **fat tails / crash risk** beyond normal skew
   - Institutional **tail hedging demand** (put spreads, call spreads for upside protection)
   - Potential **mean reversion** when fear subsides (convexity collapse → equity bounce)

3. **Convexity regimes**:
   - **High convexity (>0)**: "Platinum skew" — both wings elevated, crash + melt-up fears
   - **Low/negative convexity (<0)**: "Crystal skew" — wings cheap, linear or concave smile, complacency
   - **Asymmetric convexity**: Put wing >> Call wing = pure downside fear; Call wing >> Put wing = speculative upside

4. **Cross-sectional signal** — Ranking tickers by convexity:
   - Highest convexity → most tail risk priced → potential short-term mean reversion UP
   - Lowest convexity → complacency → trend continuation but vulnerable to gap moves

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `skew_25d` | `IV_put_25d - IV_call_25d` | Standard linear skew (positive = put premium) |
| `skew_convexity_10d` | `(IV_put_10d - 2×IV_ATM + IV_call_10d) / IV_ATM` | Butterfly convexity at 10-delta (normalized) |
| `skew_convexity_5d` | `(IV_put_5d - 2×IV_ATM + IV_call_5d) / IV_ATM` | Deep tail convexity at 5-delta |
| `skew_slope` | `(IV_put_25d + IV_call_25d - 2×IV_ATM) / IV_ATM` | Linear skew component (normalized) |
| `tail_convexity_premium` | `(actual_10d_skew - predicted_10d_skew) / IV_ATM` | Convexity beyond linear extrapolation |
| `wing_ratio_10d` | `IV_put_10d / IV_call_10d` | Put vs call wing richness (asymmetry) |

## Expected Behavior

| Regime | Convexity Signal | Expected Forward Return |
|--------|------------------|------------------------|
| Fear / Tail hedging | High positive convexity | Mean reversion UP (short-term, 1-5d) |
| Complacency | Low/negative convexity | Momentum UP (medium-term) but fragile |
| Crash pricing | Extreme put-wing convexity | Oversold bounce likely |
| Melt-up pricing | Extreme call-wing convexity | Profit-taking pullback likely |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: 7-60 DTE (focus on nearest liquid monthly/weekly)
- **Strikes**: ~10-delta (10% OTM), ~5-delta (15% OTM), ATM, 25-delta (5% OTM)
- **Liquidity filter**: Volume > 10 or OI > 100 per contract

## Approximation Method

Since yfinance doesn't provide Greeks, delta is approximated by moneyness:
- 10-delta put ≈ 10% OTM (strike ≈ 0.90 × spot)
- 5-delta put ≈ 15% OTM (strike ≈ 0.85 × spot)
- 25-delta put ≈ 5% OTM (strike ≈ 0.95 × spot)
- ATM ≈ strike ≈ spot
- 25-delta call ≈ 5% OTM (strike ≈ 1.05 × spot)
- 10-delta call ≈ 10% OTM (strike ≈ 1.10 × spot)
- 5-delta call ≈ 15% OTM (strike ≈ 1.15 × spot)

This is reasonable for liquid large-caps where IV smile is smooth. For exact deltas, Black-Scholes inversion would be needed (requires IV, rates, dividends).

## Known Limitations

1. **No historical option chains** from yfinance — requires daily snapshots stored externally
2. **Moneyness approximation** error varies with IV level, rates, dividends, time to expiry
3. **Liquidity filter** may exclude informative deep OTM strikes (especially 5-delta)
4. **Single snapshot** — cannot compute `Δconvexity_1d` without history
5. **Expiration choice** — nearest liquid may not be consistent across days (roll effects)

## Implementation Notes

### Convexity Normalization
All convexity metrics are normalized by ATM IV for cross-sectional comparison:
- Raw butterfly = `IV_put_k - 2*IV_ATM + IV_call_k` (in vol points)
- Normalized = Raw / IV_ATM (dimensionless, comparable across names)

### Tail Convexity Premium
This isolates the *non-linear* component of tail pricing:
- Predict 10-delta skew from 25-delta skew assuming linearity: `pred_10d = skew_25d * (0.10/0.05)`
- Actual 10-delta skew: `actual_10d = IV_put_10d - IV_call_10d`
- Premium = `(actual_10d - pred_10d) / IV_ATM`
- Positive = tails richer than linear skew predicts; Negative = tails cheaper

### Wing Ratio
`IV_put_10d / IV_call_10d` measures smile asymmetry:
- > 1: Put wing richer (downside fear)
- < 1: Call wing richer (upside speculation / call overwriting)
- ~1: Symmetric smile (rare for equities)

## Results (2026-10-16 close)

*Run 2026-10-18 on Friday's closing chains, nearest liquid expiry 2026-10-26 (7 DTE). The previous 2026-10-11 table was illustrative ("expected format"), not real output, and has been replaced.*

| Ticker | Price | DTE | ATM IV | 25d Skew | Conv 10d | Conv 5d | Slope | Tail Prem | Wing Ratio | Contracts (P/C) |
|--------|-------|-----|--------|----------|----------|---------|-------|-----------|------------|-----------------|
| AAPL   | 343.46 | 7 | 0.2544 | 0.0696 | 0.4325 | 0.4325 | 0.1024 | -0.2101 | 1.321 | 16 / 26 |
| SPY    | 763.25 | 7 | 0.1359 | 0.1193 | 2.2764 | 3.3379 | 0.6448 | -0.4670 | 1.862 | 72 / 51 |
| QQQ    | 709.80 | 7 | 0.2309 | 0.1234 | 0.8298 | 1.6917 | 0.1525 | -0.2950 | 1.753 | 75 / 58 |
| MSFT   | 529.05 | 7 | 0.2871 | 0.0493 | 0.7216 | 1.1112 | 0.0191 | -0.3198 | 1.018 | 19 / 25 |
| GOOGL  | 340.59 | 7 | 0.3420 | 0.0266 | 0.4194 | 0.9727 | -0.1431 | -0.0136 | 1.125 | 17 / 23 |
| AMZN   | 250.00 | 7 | 0.3439 | 0.0626 | 0.1661 | 0.4175 | -0.1551 | -0.0667 | 1.318 | 11 / 16 |

**Observations:**
- **Positive 25d skew everywhere** (put IV > call IV). Indices are steepest: QQQ 0.123, SPY 0.119.
- **SPY has by far the most convex smile** (Conv 10d 2.28, 5d 3.34, wing ratio 1.86): heavy index tail-hedge pricing.
- **Conv 5d ≥ Conv 10d for every name**, as expected (deeper wings are more convex).
- **Tail convexity premium is negative for all six**, opposite to the earlier "usually positive" claim. Check the sign convention in `main.py` before interpreting it.
- ⚠️ **Sparse single-stock wings:** AAPL's 10d and 5d IVs are identical (0.3523 / 0.2666), as are AMZN's and MSFT's 10d/5d put IV. The 5-delta strike falls back to the same farthest liquid strike. With only 11-26 contracts per side at 7 DTE, single-stock convexity is noisy. A 14-30 DTE expiry or the BS-delta refinement (Next Steps #3) would help.

## IC Analysis

**Real IC: not yet measurable.** A real forward IC needs a daily snapshot history of this signal (≥30-60 trading days), each snapshot paired with returns realized *after* it. The current `ic_analysis.py` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and is not evidence of predictive power.

**Synthetic demo only (not evidence):** the figures below come from `simulate_rolling_ic()`, which generates random data with a signal/return correlation built in. They show what the code reports when that assumption holds, nothing about this signal.

- Rolling IC mean: ~-0.18
- Information Ratio: ~-1.2
- Win rate: ~42% (negative IC means high convexity → positive returns)
- Half-life: ~12 days

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate convexity time series
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Refine delta approximation** — Use Black-Scholes to solve for exact 10/5-delta strikes
4. **Test convexity change signal** — `Δconvexity_1d` vs 1-5 day forward returns
5. **Combine with Skew Dynamics** — Multi-factor: convexity + linear skew + term structure
6. **Test regime conditioning** — Does convexity work better in high-VIX regimes?

## Files

- `main.py` — Signal computation, outputs `data/iv_skew_convexity_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "The Volatility Surface" — Jim Gatheral (smile/convexity dynamics)
- "No-Arbitrage Bounds for Convexity of Implied Volatility" — Roper (2010)
- "Tail Risk and Asset Prices" — Kelly, Jiang (2014) (tail risk premium)
- "The Variance Risk Premium and the Cross-Section of Returns" — Bollerslev, Todorov (2011)
- CBOE SKEW Index methodology (tail risk measure)
- "Model-Free Option Moments" — Bakshi, Kapadia, Madan (2003) (risk-neutral moments)