# Alpha 28 — IV Skew Dynamics

## Hypothesis

The 25-delta put-call IV skew (put IV - call IV) captures the cross-sectional pricing of tail risk. When the skew is steep (puts much more expensive than calls), the market is pricing in elevated downside risk. This skew should predict relative forward returns: tickers with elevated skew should underperform (they've already been bid up for protection), while tickers with compressed skew should outperform.

Additionally, the term structure of skew (how skew changes across expirations) provides a second dimension: if near-term skew is much steeper than far-term skew, it suggests short-dated fear that may normalize.

## Rationale

1. **Put-call skew** is driven by supply/demand for tail protection. Investors buying index puts bid up OTM put IVs relative to calls.
2. **Cross-sectional variation**: Different sectors/names exhibit different skew levels based on investor fear. High-skew names may have exhausted their put-demand premium.
3. **Term structure**: Short-term skew steepening relative to long-term suggests temporary fear that may reverse.

## Expected Decay

Skew mean-reverts within days to weeks as option supply responds to demand imbalances. Signal half-life expected at 5-15 trading days.

## Implementation

- **Near-term skew**: 25Δ put IV minus 25Δ call IV at ~30 DTE
- **Far-term skew**: same metric at ~75 DTE
- **Signal**: near_skew_25d (primary), skew_term_slope (secondary)

## Results

(See outputs from main.py and ic_analysis.py)

## Edge Cases

- ETF options may have different liquidity across expirations
- Very low IV environments can produce unreliable delta interpolation
- After-hours option chains may have stale quotes
