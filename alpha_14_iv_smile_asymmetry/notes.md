# Put/Call OI-Weighted IV Spread — Alpha Signal Notes

## Hypothesis

**Open-interest-weighted and volume-weighted IV spreads between puts and calls, along with put/call volume ratios, contain predictive information for forward equity returns by capturing institutional positioning and hedging demand.**

### Rationale

1. **Volume/OI as positioning proxy** — Unlike raw IV (which is quantized and symmetric in yfinance), volume and open interest reflect actual trading activity:
   - **High put volume/OI**: Institutional hedging, downside protection demand
   - **High call volume/OI**: Speculative longs, upside positioning, FOMO
   - **Put/Call ratio > 1**: Fear/hedging dominant → potential mean reversion bounce
   - **Put/Call ratio < 1**: Complacency/speculation dominant → potential pullback

2. **IV weighting by positioning** — Weighting IV by volume/OI emphasizes strikes where real money is positioned:
   - OI-weighted IV spread = Σ(OI × IV) / Σ(OI) for puts minus calls
   - Volume-weighted IV spread = Σ(Vol × IV) / Σ(Vol) for puts minus calls
   - More robust than median/ATM IV skew which treats all strikes equally

3. **Cross-sectional ranking power** — Ranking tickers by positioning signals:
   - Highest put/call ratio → most hedged → potential short-term outperformance
   - Lowest put/call ratio → most speculative → potential underperformance
   - Works best combined with IV rank and term structure

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `vol_ratio` | `Put_Volume / Call_Volume` | >1 = put heavy (hedging), <1 = call heavy (speculation) |
| `oi_ratio` | `Put_OI / Call_OI` | Same, using open interest (often 0 in yfinance) |
| `vol_iv_spread` | `VolWt_Put_IV - VolWt_Call_IV` | Volume-weighted IV difference |
| `vol_iv_spread_norm` | `vol_iv_spread / ATM_IV` | Normalized by ATM IV level |
| `oi_iv_spread` | `OIWt_Put_IV - OIWt_Call_IV` | OI-weighted IV difference (fallback to mean if OI=0) |
| `median_iv_spread` | `Median_Put_IV - Median_Call_IV` | Unweighted baseline |

## Expected Behavior

| Regime | Vol Ratio | Vol IV Spread | Expected Forward Return |
|--------|-----------|---------------|------------------------|
| Risk-off / Fear | > 1.5 (put heavy) | Positive | Mean reversion UP (1-5 days) |
| Risk-on / Complacency | < 0.7 (call heavy) | Negative | Pullback DOWN (1-5 days) |
| Balanced | ~1.0 | Near zero | Noise / trend continuation |
| Earnings / Catalyst | Extreme (>3 or <0.3) | Extreme | High uncertainty, reduce size |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: 7-45 DTE, aggregate top 3 liquid expiries
- **Filters**: IV ∈ (0.01, 3.0), volume > 0 or OI > 0

## Implementation Notes

### yfinance Data Limitations

1. **Open Interest = 0** for most expirations — yfinance doesn't reliably report OI. Code falls back to volume weighting and unweighted median.
2. **IV Quantization** — IV values are quantized (0.0156, 0.0312, 0.0625, 0.125, 0.25, etc.), limiting skew precision. Volume weighting mitigates this.
3. **No Historical Chains** — Requires daily snapshots stored externally for rolling IC.

### Aggregation Method

- Use top 3 expirations by DTE (7-45 DTE) to capture term structure
- Weight by volume/OI within each expiration, then aggregate
- Normalize spreads by ATM IV to make cross-sectional comparable

## Results (2026-10-16 close)

*Run 2026-10-18 on Friday's closing chains, nearest 3 expirations. Spreads are put IV minus call IV. Norm = spread / ATM IV.*

| Ticker | Price | ATM IV | P/C OI Ratio | P/C Vol Ratio | OI IV Spread (norm) | Vol IV Spread (norm) | Median Spread |
|--------|-------|--------|--------------|---------------|---------------------|----------------------|---------------|
| AAPL   | 343.46 | 0.2714 | 0.811 | 1.371 | 0.1430 (0.527) | 0.0118 (0.043) | -0.0029 |
| SPY    | 763.25 | 0.1346 | 1.224 | 1.061 | 0.0783 (0.582) | 0.0761 (0.565) | 0.0531 |
| QQQ    | 709.80 | 0.2298 | 1.828 | 1.774 | 0.1704 (0.741) | 0.1227 (0.534) | 0.0459 |
| MSFT   | 529.05 | 0.3804 | 0.417 | 0.627 | 0.0576 (0.151) | 0.0408 (0.107) | -0.0351 |
| GOOGL  | 340.59 | 0.4389 | 1.132 | 0.509 | 0.0083 (0.019) | 0.0343 (0.078) | -0.0251 |
| AMZN   | 250.00 | 0.3927 | 0.340 | 0.946 | 0.0585 (0.149) | 0.0149 (0.038) | 0.0226 |

**Observations:**
- **Indices are put-heavy:** QQQ has the highest P/C ratios (OI 1.83, volume 1.77) and the largest put premium (OI-weighted spread 0.170). SPY is put-heavy too (OI 1.22).
- **MSFT and AMZN are call-heavy by OI** (0.42 and 0.34), consistent with single-stock call speculation.
- **AAPL put volume is elevated** (vol ratio 1.37) even though OI is call-leaning. Whether this is fresh hedging is worth tracking day over day.
- OI-weighted spreads are positive for all names (puts richer than calls). The median spread is negative for AAPL, MSFT and GOOGL, so the put premium sits in the high-OI OTM strikes rather than across the whole chain.
- Normalized spreads are now sane (0.02-0.74). The 2026-10-09 values of 0.16-9.04 came from dividing by the 0.0156 placeholder ATM IV, and that table has been removed.

## IC Analysis

**Real IC: not yet measurable.** A real forward IC needs a daily snapshot history of this signal (≥30-60 trading days), each snapshot paired with returns realized *after* it. The current `ic_analysis.py` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and is not evidence of predictive power.

**Synthetic demo only (not evidence):** the figures below come from `simulate_rolling_ic()`, which generates random data with a signal/return correlation built in. They show what the code reports when that assumption holds, nothing about this signal.

- Rolling IC mean: ~-0.15 to -0.20 (negative: high put ratio → positive returns)
- Information Ratio: ~1.0-1.3
- Win rate: ~55-60%
- Half-life: ~10-15 days

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate positioning time series
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Test regime conditioning** — Does signal work better in high-VIX vs low-VIX?
4. **Combine with IV Rank + Skew** — Multi-factor: positioning + IV rank + skew + term structure
5. **Intraday validation** — Test if EOD positioning predicts next-day open-to-close returns
6. **Alternative data** — Integrate CBOE Put/Call Ratio, SpotGamma GEX for validation

## Files

- `main.py` — Signal computation, outputs `data/oi_weighted_iv_spread_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "Put/Call Ratios and Market Timing" — Martin Zweig
- "Option Volume and Stock Returns" — Pan & Potoshman (2006)
- "Dealer Gamma and Market Dynamics" — SpotGamma / SqueezeMetrics
- CBOE Equity Put/Call Ratio methodology
- "The Information Content of Option Volume" — Johnson & So (2012)