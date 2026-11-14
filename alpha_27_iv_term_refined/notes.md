# IV Term Structure Slope (Refined) — Alpha Signal Notes

## Hypothesis

**The normalized slope of the ATM IV term structure (near vs. far DTE) contains cross-sectional information about forward equity returns.**

### Rationale

1. **Term structure backwardation = fear/stress**
   - When near-term IV > far-term IV (negative normalized slope), the market prices elevated near-term uncertainty
   - This typically occurs around earnings, macro events, or sudden risk-off moves
   - **Mean-reversion signal**: Extreme backwardation → subsequent IV normalization → equity bounce (short-term mean reversion)

2. **Term structure contango = complacency**
   - When far-term IV > near-term IV (positive normalized slope), the market expects normal/calm conditions
   - Sustained contango reflects risk-on / complacency regime
   - **Trend-following signal**: High contango → trend continuation (medium-term), but extreme contango → vulnerability to shock

3. **Cross-sectional ranking**
   - Ranking tickers by normalized slope allows relative-value positioning
   - Most backwardated tickers (most negative slope) = highest stress = potential mean-reversion longs
   - Most contango tickers (most positive slope) = most complacent = potential underweight/short

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `slope_norm_pct` | `(IV_far - IV_near) / IV_near * 100` | Normalized term structure slope in percent |
| `near_atm_iv` | ATM IV at ~7 DTE | Near-term vol expectation |
| `far_atm_iv` | ATM IV at ~49 DTE (or farthest available) | Medium-term vol expectation |

**Parameters:**
- `NEAR_DTE = 7` (skips 0-DTE weekly noise)
- `FAR_DTE = 49` (max available in yfinance; falls back to farthest available)
- Liquidity filter: `volume > 5 OR OI > 50`
- ATM filter: median IV of strikes within ±2% moneyness, IV > 5%

## Data Source & Limitations

**Source:** yfinance option chains (live snapshot)

**Key Limitations:**
1. **yfinance IV quality** — Many chains return placeholder IV values (0.0625 = 6.25%), especially for near-term expirations. This causes false-zero slopes.
2. **Limited DTE range** — yfinance typically only offers up to ~49-77 DTE, not the ideal 90-120 DTE for a clean term structure.
3. **Single snapshot** — No historical time series; IC analysis requires accumulating daily snapshots.
4. **Calls-only ATM** — Uses calls only for ATM IV; puts redundant for liquid names but could differ for skew.

## Empirical Findings (Preliminary)

From live run on 2026-10-30:
- 16 tickers returned data
- 15 of 16 showed 0.00% slope (both near/far IV = 0.0625 placeholder)
- 1 ticker (DIA) showed 416% slope (real IV spread: 6.25% → 32.28%)

**Interpretation:** The signal infrastructure works, but yfinance IV data quality is insufficient for live trading. Need:
- Paid data (Polygon, ORATS, Cboe) for reliable IV
- Historical accumulation for rolling IC
- Better near-term IV extraction (filter 0-DTE/placeholder chains)

## Next Steps

1. **Data upgrade**: Switch to Polygon.io or ORATS for clean IV surfaces
2. **History building**: Run daily and accumulate in `data/iv_term_refined_history.json`
3. **Rolling IC**: Implement `rolling_ic()` from `common.utils` once >60 days of history
4. **Pre-registration**: Define IC test parameters before expanding history
5. **Tradability filter**: Add VIX futures validation (like alpha_03)

## Files

- `main.py` — Live signal computation
- `ic_analysis.py` — IC framework (placeholder until history accumulates)
- `data/iv_term_refined_latest.csv` — Latest cross-sectional snapshot
- `data/iv_term_refined_ic.txt` — IC analysis output