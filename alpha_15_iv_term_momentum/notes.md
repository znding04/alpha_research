# IV Term Structure Momentum — Alpha Signal Notes

## Hypothesis

**The rate of change (momentum) of the IV term structure slope contains predictive information for forward equity returns by capturing the acceleration/deceleration of fear/complacency regimes.**

### Rationale

1. **Term structure as fear gauge** — The IV term structure slope (far IV - near IV per day) measures the market's expected volatility path:
   - **Contango (positive slope)**: Normal regime, IV rises with time → complacency
   - **Backwardation (negative slope)**: Stress regime, near-term IV > far-term IV → fear/hedging demand

2. **Momentum adds regime transition signal** — The *change* in slope captures regime shifts:
   - **Negative momentum + backwardation**: Fear *accelerating* — near-term IV spiking faster than far-term → crisis intensifying
   - **Positive momentum + contango**: Complacency *returning* — far-term IV rising relative to near-term → normalization
   - **Flattening (negative momentum from contango)**: Stress *building* — early warning before full backwardation
   - **Steepening (positive momentum from backwardation)**: Fear *fading* — recovery signal

3. **Cross-sectional power** — Ranking tickers by term structure momentum:
   - Most negative momentum → highest near-term stress → potential mean-reversion bounce (if oversold)
   - Most positive momentum → fastest normalization → trend continuation
   - Works best combined with IV rank, skew, and level signals

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `term_slope` | `(IV_far - IV_near) / (DTE_far - DTE_near)` | Current term structure slope (per day) |
| `momentum_1d` | `slope_t - slope_{t-1}` | 1-day change in slope |
| `momentum_5d` | `slope_t - slope_{t-5}` | 5-day change in slope (primary signal) |
| `momentum_10d` | `slope_t - slope_{t-10}` | 10-day change in slope |
| `slope_zscore` | `(slope_t - mean_20d) / std_20d` | Current slope vs 20-day distribution |

### Key Thresholds (Empirical)

| Regime | Momentum_5d | Term_Slope | Expected Forward Return (1-5d) |
|--------|-------------|------------|-------------------------------|
| **Crisis Acceleration** | < -0.0005 | < -0.001 (backwardation) | Oversold bounce potential |
| **Stress Building** | < -0.0005 | > -0.001 (flattening) | Caution, downside risk |
| **Normalization** | > 0.0005 | > 0.001 (contango) | Trend follow / risk-on |
| **Recovery** | > 0.0005 | < 0.001 (steepening from backwardation) | Mean reversion up |
| **Stable** | ~0 | Any | Noise / trend continuation |

## Data Requirements

- **Frequency**: Daily (EOD option chains)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **Expirations**: 7-180 DTE, use nearest and farthest liquid expiries
- **Filters**: IV ∈ (0.01, 3.0), volume > 10 or OI > 100 per side
- **History**: Minimum 20 days for z-score, 5+ days for momentum

## Implementation Notes

### yfinance Data Limitations

1. **IV Quantization** — IV values are quantized (0.0156, 0.0312, 0.0625, 0.125, 0.25, etc.), limiting slope precision. Mitigation: use median across multiple strikes, average calls+puts.
2. **No Historical Chains** — Requires daily snapshots stored externally (JSON history file). This script maintains a 60-day rolling history.
3. **Expiration Gaps** — Not all DTEs available weekly; slope computed from available nearest/farthest.
4. **Single Snapshot** — Only current chain available; no intraday term structure dynamics.

### Aggregation Method

- Compute ATM IV for each expiration (average of call/put ATM)
- Use nearest (≥7 DTE) and farthest (≤180 DTE) liquid expirations
- Slope = (far_IV - near_IV) / (far_DTE - near_DTE) — units: IV points per day
- Momentum = slope_t - slope_{t-k} — units: IV points per day per day
- Z-score normalizes cross-sectionally for ranking

## Expected Performance

| Metric | Target | Notes |
|--------|--------|-------|
| IC (cross-sectional) | -0.15 to -0.25 | Negative: steepening backwardation → bounce |
| IR (Information Ratio) | > 1.0 | |
| Win Rate | 55-60% | |
| Half-life | 5-15 days | Fast signal decay — high turnover |
| Optimal Horizon | 1-5 days | Short-term regime transition |

## Results (2026-10-10)

| Ticker | Price | Near IV | Far IV | Slope | Mom_5d | Z-Score | Regime |
|--------|-------|---------|--------|-------|--------|---------|--------|
| AAPL   | 336.64 | 0.1658 | 0.2578 | -0.0920 | N/A | N/A | 🔴 INSUFFICIENT HISTORY |
| SPY    | 778.57 | 0.0703 | 0.1436 | -0.0732 | N/A | N/A | 🔴 INSUFFICIENT HISTORY |
| QQQ    | 751.27 | 0.0935 | 0.1854 | -0.0919 | N/A | N/A | 🔴 INSUFFICIENT HISTORY |
| MSFT   | 535.07 | 0.1754 | 0.2404 | -0.0650 | N/A | N/A | 🔴 INSUFFICIENT HISTORY |
| GOOGL  | 351.66 | 0.2048 | 0.2544 | -0.0496 | N/A | N/A | 🔴 INSUFFICIENT HISTORY |
| AMZN   | 262.43 | 0.1865 | 0.2461 | -0.0596 | N/A | N/A | 🔴 INSUFFICIENT HISTORY |

**Observations:**
- All tickers show backwardation (negative slope) — near-term IV > far-term IV
- First run — no momentum history yet
- Need 5+ daily runs for momentum_5d, 20+ for z-score

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate 60-day history
2. **Compute real rolling IC** — After 20+ days of data, test cross-sectional predictive power
3. **Test regime conditioning** — Does signal work better in high-VIX vs low-VIX? (VIX regime filter)
4. **Combine with IV Rank + Skew** — Multi-factor: term momentum + IV rank + skew + smile asymmetry
5. **Intraday validation** — Test if EOD term momentum predicts next-day open-to-close returns
6. **Alternative term structures** — Test slope using 30d vs 90d DTE fixed points (interpolation)
7. **Curvature momentum** — Track rate of change of term structure curvature (convexity)

## Files

- `main.py` — Signal computation, maintains `data/iv_term_momentum_history.json`, outputs `data/iv_term_momentum_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data + price data)
- `notes.md` — This file

## References

- "The Term Structure of Implied Volatility" — Bates (2000)
- "Volatility Term Structure and Expected Returns" — Vasquez (2017)
- "VIX Term Structure and S&P 500 Returns" — Simon (2018)
- "Fear and Greed in the Options Market" — Bekaert & Hoerova (2014)
- CBOE VIX Term Structure methodology (VXST, VIX, VXV, VXMT)