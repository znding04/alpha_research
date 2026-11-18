# ATM IV Term-Structure Convexity — Alpha Signal Notes

## Hypothesis

**The curvature of the ATM implied-vol term structure (ATM IV ~14d / ~30d / ~75d) predicts cross-sectional forward equity returns.** A humped curve (rich mid-tenor vol) is a classic stress/forward-looking volatility signal; a trough (cheap mid-tenor) suggests smooth contango. Let the IC determine the sign.

### Rationale

1. **ATM IV term-structure slope is already an existing factor (alpha_03, 25, 27, 37).** Adding curvature introduces an orthogonal dimension: slope tells you if long-term vol is higher/lower than short-term, but curvature tells you whether the middle tenor is an outlier relative to the wings. This is a more granular measure of term-structure shape and potential event risk.
2. **Humped curves imply market pricing of intermediate event risk.** When the ~30d belly is rich compared to the ~14d and ~75d wings, market participants are pricing expected volatility in the medium term (e.g., upcoming earnings, macro releases, geopolitical events) that is not reflected in the short-term front or long-term forward views.
3. **Cross-sectional ranking over the 6 focus tickers (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN) isolates the relative quality of term-structure curvature.** Focusing on these large-cap names reduces noise from sector/ ETF-specific effects and makes the signal comparable across instruments.
4. **ATM vs. skew: this signal is distinct from skew-based alphas (02, 28, 42, 35).** ATM IV curvature is a pure term-structure characteristic, independent of skew/OTM asymmetry.

## Signal Definition

| Step | Calculation |
|------|-------------|
| Target tenors | Short ≈ 14 days, Mid ≈ 30 days, Long ≈ 60–75 days (nearest available expiration) |
| ATM IV per tenor | Median IV of strikes within ±2% moneyness (IV > 5%) |
| Curvature | `curvature = IV_mid - 0.5 * (IV_short + IV_long)` |
| Normalized curvature | `curvature_norm = curvature / IV_mid` (scale-free, cross-section comparable) |
| Slope (reference only) | `slope = (IV_long - IV_short) / IV_short` (an existing factor alpha_37/27) |
| Cross-sectional rank | Percentile rank over the 6 focus names (higher = richer mid-tenor belly) |

**Interpretation**

- `curvature > 0` → humped term structure (mid-tenor vol rich vs wings; near-term event risk priced into the belly)
- `curvature < 0` → trough (belly cheap; smooth contango or flat curve)
- `curvature_norm` enables direct comparison across tickers despite different IV levels
- `curvature_rank` is the signal used for IC testing (1 = richest mid-tenor belly)

## Hypotheses to test

- **H1 (return prediction):** cross-sectional curvature rank predicts forward equity returns over 5–21 days. Expectation ambiguous: rich belly could mean fear/mean-reversion (bearish) or event setup (bullish), let the IC decide.
- **H2 (vol prediction):** rich curvature predicts a *fall* in forward realized vol (vol mean-reversion). This is the more likely edge and aligns with existing VRP-term-structure findings.

## Data Source & Limitations

**Source:** yfinance option chains (nearest expiration) + yfinance daily OHLC history (1y).

**Limitations:**

1. **Market‑closed degenerate IVs.** The script runs at 02:00 ET via cron on the Mac Mini. After‑hours option chains are often a single expiration with a default `impliedVolatility = 0.0625`. The guards (`IV > 0.01` / `IV > 0.05`) reduce but cannot eliminate this. A snapshot when the market is closed may show degenerate IVs across many tickers — treat such snapshots as data‑quality flagged, not as signal.
2. **Expiration selection noise.** If the market has thin liquids on one tenor (e.g., no 30‑day contracts), the nearest is ~28d or ~31d; curvature may jump as a data artifact rather than a true market move. The signal is designed to be robust to missing one tenor (it returns None if the three selected are not distinct), but this also reduces snapshot success rates when the chain is thin.
3. **Cross‑section bench size.** The focus set is only 6 names; historical IC requires ≥60 daily snapshots to achieve statistical significance (t-stat ≈ 2.0). On early days, the cross‑section may be smaller (fewer tickers have valid data), leading to noisy single‑day IC.
4. **Term‑structure smoothness.** Real markets price the term structure smoothly; large curvature may reflect transient illiquidity in the middle tenor rather than a genuine pricing inefficiency. However, some curvature is expected (short‑term fear vs long‑term calm) and the signal tests whether this relative pricing is systematically informative.

## Why this is a distinct alpha

- **Term‑structure curvature is orthogonal to slope.** Existing alpha_03, 25, 27, 37, 37 measure slope (long vs short). They cannot capture a humped/trough shape when the slope is zero or modest.
- **ATM IV curvature is orthogonal to skew.** Existing skew alphas (02, 28, 42, 35) measure put vs call asymmetry. They do not touch the vertical dimension (short/mid/long).
- **This signal is new to this repo.** No existing alpha computes a three‑tenor ATM butterfly curvature across the term structure; they are either pure slope, pure skew, or pure percentile rank of a single tenor.

## Historical analysis vs live snapshots

- **Historical version (`alpha_45_iv_term_convexity/historical.py`).** TBD. In future cron runs, a historical version would use CBOE term‑structure indices (VIX9D, VIX, VIX3M, VIX6M, SKEW, COR3M) where available; the focus set would be those with term‑structure data (SPY, QQQ, IWM, DIA, TLT, EEM). Curvature would be derived from the four‑point IV surface.
- **Live snapshots.** The current `main.py` computes curvature from yfinance option chains and writes `data/iv_term_convexity_latest.csv`. The `collect_snapshots.py` orchestrator (run daily) archives snapshots in `data/snapshots/<YYYY-mm-dd>/` and a post‑processor (not yet written) would accumulate snapshots for historical IC testing.

## Notes for development & debugging

- If you see degenerate IVs (0.0625) for many tickers, check the script’s run time (cron is 02:00 ET). Shift to a U.S. afternoon run (e.g., 22:00 ET) to get real‑time chains.
- To test expiration selection logic, add `print(f"Exps: {[e for e in tq.options[:10]]}")` in `get_atm_iv`.
- The `TENOR_SHORT/MID/LONG` constants should be tuned based on available expirations. Some markets only have 7, 21, 30 DTEs; consider using `min()` across targets.
- The script depends on `common/universe.py` (TICKERS) and `common/utils.py` (none for this signal, but the pattern includes `ic_analysis.py` for testing).
- When adding a historical version, reference `alpha_03_iv_term_structure/historical.py` for the pattern of loading CBOE term‑structure indices and calculating slope/curvature.