# IV Skew Momentum (Refined)

## Hypothesis
5-day change in 25-delta put-call skew (call_IV - put_IV) predicts forward returns:
- **Positive Δ(skew)** (call skew increasing) → bullish momentum → expect higher returns
- **Negative Δ(skew)** (put skew increasing / call skew decreasing) → bearish momentum → expect lower returns

## Rationale
- Skew reflects market's view on relative tail risk: 
  - **Put skew** (put_IV > call_IV) → demand for downside protection
  - **Call skew** (call_IV > put_IV) → demand for upside exposure
- **Momentum in skew** indicates shifting risk appetite: 
  - Rising put skew → increasing fear → potential downside
  - Rising call skew → increasing optimism → potential upside
- Black-Scholes delta is more precise than fixed moneyness for strike selection

## Signal Definition
- **Signal**: Δ(skew) over 5 trading days = skew_t - skew_{t-5}
- **Cross-sectional**: Rank tickers by Δ(skew) daily
- **Long**: High Δ(skew) (call skew rising)
- **Short**: Low Δ(skew) (put skew rising / call skew falling)

## Data Requirements
- **Daily snapshots** of 25-delta IV for calls and puts (to compute skew)
- **Accumulated history** for 5-day Δ(skew) (current snapshot minus 5-day lag)
- **Forward returns** for IC testing (5-day forward return)

## Cross-Sectional Test
- Rank tickers by Δ(skew) each day
- Compute Spearman IC between signal rank and 5-day forward return
- **Pass**: |t| ≥ 2, same sign as hypothesized, and positive OOS alpha after cost adjustment

## Limitations
- Requires accumulated snapshots (not live-only)
- Skew extraction depends on liquid 25-delta options
- Skew may be noisy; smoothing may be needed