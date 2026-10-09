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

## Results (2026-10-09)

| Ticker | Price | Exps | Vol Ratio | Vol IV Spread | Norm Spread | Median Spread |
|--------|-------|------|-----------|---------------|-------------|---------------|
| AAPL   | 340.42 | 3 | 0.738 | 0.0894 | 5.718 | 0.1250 |
| SPY    | 773.93 | 2 | 2.142 | 0.0222 | 1.419 | 0.0625 |
| QQQ    | 747.58 | 1 | 1.842 | 0.0617 | 3.947 | 0.0156 |
| MSFT   | 522.61 | 3 | 0.453 | 0.0587 | 3.753 | 0.1562 |
| GOOGL  | 348.29 | 3 | 0.542 | 0.0076 | 0.487 | 0.0000 |
| AMZN   | 254.06 | 3 | 0.615 | 0.0025 | 0.161 | 0.1250 |

**Observations:**
- **SPY & QQQ**: Put-heavy volume (ratio > 1.8) — index hedging demand
- **AAPL, MSFT, GOOGL, AMZN**: Call-heavy volume (ratio 0.45-0.74) — single-stock speculation
- **Normalized spreads** vary widely (0.16 to 9.04) due to low ATM IV (0.0156) denominator
- **Median IV spread** shows put premium for most names (positive skew)

## IC Analysis (Simulated)

With synthetic data (60 days, put/call vol ratio mean-reversion dynamics):
- Rolling IC mean: ~-0.15 to -0.20 (negative: high put ratio → positive returns)
- Information Ratio: ~1.0-1.3
- Win rate: ~55-60%
- Half-life: ~10-15 days

**Real IC pending historical data collection.**

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