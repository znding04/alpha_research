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
- Single fit on OTM options only (puts K < S, calls K ≥ S, live bid); ITM IVs are noisy
- Expiration closest to 30 DTE (7–60 DTE window)
- Require ≥5 liquid points, R² > 0.5 preferred

### Normalization
- Raw curvature has units of IV/moneyness² — not comparable across tickers
- Normalize: `normalized_curvature = curvature / ATM_IV`
- This is the "vol of vol" proxy in dimensionless form
- Not comparable across tenors (m² scales with T); use `rel_butterfly` for regimes

### Butterfly Approximation
- From the quadratic: `(IV(+m) + IV(−m))/2 − IV(0) = c·m²`
- 25Δ strikes sit at `m ≈ N⁻¹(0.75)·σ_ATM·√T ≈ 0.674·σ√T` in log-moneyness
- `butterfly_25d = c · (0.674·σ_ATM·√T)²` in IV units (0.01 = 1 vol point)
- `rel_butterfly = butterfly_25d / ATM_IV`; regime: High > 2.5%, Low < 1.0% (provisional until history exists)
- *(Before 2026-10-18 a fixed Δm² = 0.0225 was used — ~10× too large at 7–30 DTE)*

### Known Limitations
1. **Single expiration** — Using ~30 DTE expiry ignores term structure of curvature
2. **yfinance gamma often NaN** — Relies on quadratic fit rather than gamma sum
3. **No historical option chains** — Requires daily snapshots stored externally
4. **After-hours bid/ask** — Often zero; relies on lastPrice-derived IV
5. **Moneyness window fixed** — 30% may be too wide/narrow for some tickers
6. **Quadratic smile** — Can't capture put/call wing asymmetry beyond the linear skew term

## Results — expanded ETF universe (2026-10-16 close)

Universe: 12 ETFs (SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO) + AAPL, MSFT, GOOGL, AMZN, from `common/universe.py`. Raw: `data/snapshots/2026-10-16/`.

| ticker | dte | atm_iv | butterfly_25d | rel_butterfly | r2 |
|---|---|---|---|---|---|
| SPY | 33 | 0.1569 | 0.0019 | 0.0120 | 0.9780 |
| QQQ | 33 | 0.2261 | 0.0037 | 0.0165 | 0.9750 |
| IWM | 33 | 0.1946 | 0.0049 | 0.0250 | 0.9459 |
| DIA | 33 | 0.1539 | 0.0023 | 0.0148 | 0.9880 |
| GLD | 33 | 0.2128 | 0.0044 | 0.0207 | 0.9842 |
| SLV | 33 | 0.3622 | 0.0095 | 0.0262 | 0.9892 |
| TLT | 33 | 0.1497 | 0.0032 | 0.0212 | 0.9871 |
| EEM | 33 | 0.2608 | 0.0083 | 0.0319 | 0.9504 |
| EWZ | 33 | 0.5968 | -0.0075 | -0.0126 | 0.9251 |
| FXI | 33 | 0.2695 | -0.0030 | -0.0111 | 0.4416 |
| GDX | 33 | 0.4143 | 0.0101 | 0.0244 | 0.9069 |
| USO | 33 | 0.4712 | 0.0148 | 0.0313 | 0.9235 |
| AAPL | 33 | 0.2810 | 0.0036 | 0.0129 | 0.9492 |
| MSFT | 33 | 0.3278 | 0.0040 | 0.0121 | 0.9525 |
| GOOGL | 33 | 0.3767 | 0.0060 | 0.0160 | 0.8451 |
| AMZN | 33 | 0.4079 | 0.0062 | 0.0152 | 0.8869 |

**ETF vs single-name observations:**
- Relative butterfly is lowest for SPY (1.2%) and highest for USO/EEM (3.1–3.2%); commodities and EM carry more priced jump risk than broad indices.
- EWZ and FXI give negative curvature; FXI's fit is unreliable (R² 0.44, thin chain). Single names (1.2–1.6%) are close to the index level at 33 DTE.

## Results (2026-10-16 close, run 2026-10-18)

Expiration used: 2026-11-20 (33 DTE) for all tickers.

| Ticker | Price | ATM IV | Skew (linear) | Curvature (raw) | Butterfly 25Δ | Rel. Butterfly | Regime | Fit R² | Points |
|--------|-------|--------|---------------|-----------------|---------------|----------------|--------|--------|--------|
| AAPL   | 343.46 | 0.2810 | -0.286 | 1.114 | 0.0036 | 1.29% | Normal | 0.95 | 37 |
| SPY    | 763.25 | 0.1569 | -0.705 | 1.860 | 0.0019 | 1.20% | Normal | 0.98 | 148 |
| QQQ    | 709.80 | 0.2261 | -0.655 | 1.777 | 0.0037 | 1.65% | Normal | 0.98 | 171 |
| MSFT   | 529.05 | 0.3278 | -0.249 | 0.894 | 0.0040 | 1.21% | Normal | 0.95 | 59 |
| GOOGL  | 340.59 | 0.3767 | -0.123 | 1.031 | 0.0060 | 1.60% | Normal | 0.85 | 41 |
| AMZN   | 250.00 | 0.4079 | -0.164 | 0.908 | 0.0062 | 1.52% | Normal | 0.89 | 30 |

Raw: `data/iv_surface_curvature_latest.csv`. Butterfly in IV units (0.0036 = 0.36 vol points).

**Fixes in this run (2026-10-18):**
- 25Δ butterfly used a fixed Δm² = 0.0225; the correct 25Δ log-moneyness at 30 DTE is only ~0.03–0.08, so the old values (0.29–0.34) were ~10× too large. Now uses `0.674·σ√T`.
- Fit uses OTM options only and a ~30 DTE expiry (was nearest ≥7 DTE with ITM strikes included); R² improved to 0.85–0.98 (AMZN 0.32 → 0.89).
- Regime thresholds moved to relative butterfly; the old normalized-curvature thresholds labelled every name "High".

**Observations:**
- 25Δ flies of 0.2–0.6 vol points are realistic for 1-month equity smiles.
- Index ETFs have the steepest linear skew (SPY −0.71, QQQ −0.66) and highest raw curvature; single names have flatter skew but similar relative wing premium.
- QQQ and GOOGL have the richest wings relative to ATM (~1.6%); SPY the cheapest (1.2%).
- The 11-20 expiry includes earnings for the single names, which lifts ATM IV and depresses relative curvature.

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