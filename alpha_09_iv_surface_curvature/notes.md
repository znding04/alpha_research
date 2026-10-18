# IV Surface Curvature — Alpha Signal Notes

## Hypothesis

**The curvature (convexity) of the implied volatility smile contains predictive information for forward equity returns and tail risk.**

### Rationale

1. **Smile curvature = jump risk premium** — The IV smile's curvature (second derivative w.r.t. strike/moneyness) reflects the market's pricing of jump risk and tail events. A steep smile (high curvature) indicates strong demand for OTM options as crash insurance.

2. **Butterfly spreads as pure curvature** — A butterfly spread (long wings, short body) isolates curvature risk:
   - Long OTM put + Long OTM call - 2× ATM straddle
   - Pays off when realized volatility has fat tails (jumps)
   - Price of butterfly = market's expectation of kurtosis

3. **Cross-sectional ranking** — Ranking tickers by normalized smile curvature:
   - **Highest curvature**: Market pricing extreme tail risk → potential mean-reversion bounce if fear is excessive, OR genuine crash risk
   - **Lowest curvature**: Complacency, "flat" smile → trend continuation but vulnerable to gap moves
   - **Normal curvature**: Balanced risk pricing → earn volatility risk premium

4. **Curvature dynamics** — Change in curvature (Δcurvature) may be more predictive than level:
   - **Curvature spiking up**: Sudden demand for tail protection → short-term reversal or volatility expansion
   - **Curvature collapsing**: Complacency setting in → trend continuation or "calm before storm"

5. **Relationship to other signals**:
   - Curvature is orthogonal to ATM IV level (VRP) and linear skew
   - Skew = 1st derivative (directional bias), Curvature = 2nd derivative (tail risk)
   - Together: Level + Skew + Curvature = complete smile description

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `curvature` | Quadratic coefficient `c` in `IV = a + b·m + c·m²` | Raw curvature (IV/moneyness²) |
| `normalized_curvature` | `curvature / ATM_IV` | Dimensionless, comparable across tickers |
| `butterfly_25d` | `curvature × 0.15² ≈ curvature × 0.0225` | Approx 25-delta butterfly in vol points |
| `skew` | Linear coefficient `b` | Put-call skew (already in alpha_02) |
| `atm_iv` | Constant term `a` | ATM IV level (already in alpha_01/04) |

Where `m = ln(K/S)` = log moneyness.

## Expected Behavior

| Regime | Curvature Signal | Expected Forward Return |
|--------|-----------------|------------------------|
| Panic / Crash | Very high curvature | Mean reversion UP (1-5 days) OR further crash |
| Risk-off / Fear | High curvature | Volatility expansion, potential bounce |
| Normal | Moderate curvature (~0.03-0.08) | Earn volatility risk premium |
| Complacent / Risk-on | Low curvature (< 0.02) | Momentum UP, but gap risk |
| Curvature spike (Δ > 0) | Sudden tail hedging | Short-term reversal likely |
| Curvature crash (Δ < 0) | Complacency returning | Trend continuation |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **IV source**: Nearest liquid expiration (7-45 DTE)
- **Fitting**: Quadratic polynomial in log-moneyness space
- **Liquidity filter**: Volume > 10 or OI > 100 per leg
- **Moneyness range**: |ln(K/S)| ≤ 0.3 (≈30% OTM)
- **Weighting**: By volume + OI for robust fitting

## Implementation Notes

### Quadratic Smile Fitting
- Fit `IV = a + b·m + c·m²` where `m = ln(K/S)`
- Weighted by liquidity (volume + open interest)
- Separate fits for calls and puts, then average
- Require ≥5 liquid points per side, R² > 0.5 preferred

### Normalization
- Raw curvature has units of IV/moneyness² — not comparable across tickers
- Normalize: `normalized_curvature = curvature / ATM_IV`
- This is the "vol of vol" proxy in dimensionless form
- Typical range: 0.01 (flat) to 0.15+ (steep smile)

### Butterfly Approximation
- 25-delta butterfly ≈ curvature × (Δm)²
- Δm for 25-delta ≈ ln(1.05) - ln(0.95) ≈ 0.10 → (0.10)² = 0.01
- Using 0.0225 as conservative multiplier
- Gives butterfly in same units as IV (annualized vol points)

### Known Limitations
1. **Single expiration** — Using nearest expiry ignores term structure of curvature
2. **yfinance gamma often NaN** — Relies on quadratic fit rather than gamma sum
3. **No historical option chains** — Requires daily snapshots stored externally
4. **After-hours bid/ask** — Often zero; relies on lastPrice-derived IV
5. **Moneyness window fixed** — 30% may be too wide/narrow for some tickers
6. **Call/put asymmetry** — Averaging assumes symmetric smile; puts often steeper

## Results (2026-10-16 close, run 2026-10-18)

Expiration used: 2026-10-26 (7 DTE) for all tickers.

| Ticker | Price | ATM IV | Skew (linear) | Curvature (raw) | Norm. Curvature | Butterfly (25d) | Fit R² | Points |
|--------|-------|--------|---------------|-----------------|-----------------|-----------------|--------|--------|
| AAPL   | 343.46 | 0.2588 | -0.7026 | 15.06 | 58.20 | 0.3389 | 0.84 | 42 |
| SPY    | 763.25 | 0.1350 | -1.7507 | 13.35 | 98.90 | 0.3004 | 0.97 | 122 |
| QQQ    | 709.80 | 0.2399 | -1.1213 | 14.23 | 59.30 | 0.3201 | 0.93 | 128 |
| MSFT   | 529.05 | 0.2749 | -0.6218 | 12.69 | 46.16 | 0.2855 | 0.90 | 44 |
| GOOGL  | 340.59 | 0.3164 | -0.6903 | 14.94 | 47.22 | 0.3361 | 0.92 | 40 |
| AMZN   | 250.00 | 0.3212 | -0.3715 | 1.79 | 5.56 | 0.0402 | 0.32 | 27 |

Raw: `data/iv_surface_curvature_latest.csv`.

**Observations:**
- Negative linear skew and positive curvature for all names (normal equity smile).
- SPY has the steepest skew and highest normalized curvature, consistent with index put demand.
- AMZN's fit is poor (R² 0.32, only 27 points) — its curvature/butterfly values are not reliable this run.
- **Suspicious:** butterfly (25d) values of ~0.30–0.34 vol points are implausibly large for a 7-DTE smile (typical 25Δ fly is a few vol points). Likely the 25Δ strikes are being approximated too far OTM at short DTE, or the fly is computed from the fitted quadratic far outside the data. Every name is also labelled "High Curvature", so the classification threshold is uncalibrated. Check the 25Δ strike mapping and use a ~30 DTE expiry.

## IC Analysis (Simulated)

With synthetic data (60 days, mild positive correlation between curvature and returns):
- Rolling IC mean: ~0.05-0.10
- Information Ratio: ~0.5-1.0
- Win rate: ~52-55%
- Half-life: ~15-20 days

**Interpretation**: Weak positive IC expected (curvature as fear gauge → mean reversion).

**⚠️ These are synthetic demo numbers, not evidence of predictive power.** `simulate_rolling_ic()` generates returns as `signal * k + noise`, so a positive/negative IC is baked in by construction. Separately, `run_ic_analysis()` correlates today's signal with the *past* 5-day return (`Close[-6] → Close[-1]`), which is not a forward IC and cannot test predictability.

**Real IC: not yet measured.** Requires daily signal snapshots (≥30–60 trading days) paired with true forward returns.

## Next Steps

1. **Run main.py daily** — Build curvature time series via cron
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Test curvature change signal** — `Δnormalized_curvature_1d` vs 1-5 day forward returns
4. **Combine with VRP + Skew + Term Structure** — Multi-factor: Curvature + VRP + Skew + Term Slope
5. **Test regime-dependent IC** — High VIX vs low VIX regimes
6. **Add term structure of curvature** — Curvature slope across expirations (curvature term structure)
7. **Compare with VIX term structure** — For SPY, benchmark against S&P 500 variance term structure

## Files

- `main.py` — Signal computation, outputs `data/iv_surface_curvature_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "The Volatility Smile" — Derman (1999)
- "Model-Free Implied Volatility and the Volatility Smile" — Britten-Jones & Neuberger (2000)
- "Tail Risk and Asset Prices" — Kelly, Jiang, et al. (2016)
- "Volatility of Volatility and the Cross-Section of Returns" — Huang & Shaliastovich (2014)
- "Butterfly Spreads and the Implied Volatility Smile" — Javaheri (2005)
- "Crash Risk and the Cross-Section of Expected Returns" — Bollerslev, Todorov (2011)