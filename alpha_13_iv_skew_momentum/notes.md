# IV Skew Momentum — Alpha Signal Notes

## Hypothesis

**Core idea**: The *rate of change* of put-call IV skew (25-delta) contains predictive information beyond the skew level itself.

- **Skew steepening** (momentum > 0): Accelerating put buying / call selling → rising fear, hedging demand, or informed downside positioning. May precede:
  - Continued downside (momentum persistence)
  - Mean-reversion bounce (overbought fear)
  
- **Skew flattening** (momentum < 0): Complacency, call buying, put selling → low fear premium. May precede:
  - Continued upside (complacency persistence)
  - Sudden skew steepening event (vol event risk)

## Signal Construction

1. **Universe**: AAPL, SPY, QQQ, MSFT, GOOGL, AMZN (liquid, diverse sectors)
2. **Skew measure**: 25-delta put IV - 25-delta call IV (approximated via 0.95/1.05 moneyness)
3. **Expiration**: Nearest liquid (7-45 DTE) to capture near-term sentiment
4. **Momentum**: (Current skew - Skew 5 days ago) / 5 — daily rate of change
5. **Regime filters**: 
   - Skew z-score (current vs 20-day history) — extreme levels may mean-revert
   - Skew volatility (20-day std) — high vol = noisy signal

## Expected Decay Horizon

- **Short-term (1-5 days)**: Momentum persistence — fear/complacency tends to cluster
- **Medium-term (5-20 days)**: Mean-reversion — extreme skew changes often overshoot
- **Long-term (>20 days)**: No predictive power — skew level matters more than change

## Cross-Sectional Approach

Rank tickers by skew momentum each day:
- **Long**: Most negative momentum (skew flattening fastest → complacency → potential vol event)
- **Short**: Most positive momentum (skew steepening fastest → fear peaking)
- **Neutral**: Middle quintiles

Alternative: Sort by skew z-score for mean-reversion (long extreme negative z, short extreme positive z).

## Risk Factors

1. **Earnings/events**: Skew naturally steepens pre-earnings — must filter or adjust
2. **Expiration rolling**: DTE changes affect skew level — use constant-maturity or DTE-matched
3. **Liquidity**: 25-delta approximation breaks down in illiquid names
4. **Regime shifts**: 2020/2022 regime changes alter skew baseline

## Data Requirements

- Daily skew snapshots (run main.py daily via cron)
- Minimum 20 days for momentum calculation
- 60+ days for rolling IC analysis
- Forward returns: 1-day, 5-day, 10-day horizons

## Testing Plan

1. **Accumulate history**: Run daily for 60+ trading days
2. **Compute IC**: Cross-sectional Spearman rank IC vs 1d/5d/10d forward returns
3. **Rolling IC**: 60-day window to assess stability
4. **Signal metrics**: IR, win rate, half-life, max drawdown
5. **Regime analysis**: IC conditioned on VIX level, market trend
6. **Look-ahead check**: Ensure no future data leakage in skew calculation

## Relationship to Existing Signals

| Signal | Folder | Relationship |
|--------|--------|--------------|
| IV Skew Dynamics (level) | alpha_02 | This is the *level*; momentum is the *derivative* |
| IV Term Structure | alpha_03 | Skew term structure vs skew momentum |
| VRP | alpha_04 | VRP = IV² - RV²; skew momentum captures IV asymmetry change |
| IV Momentum | alpha_12 | ATM IV trend vs skew (OTM) trend |

## Implementation Notes

- Uses JSON history file (`data/iv_skew_momentum_history.json`) for persistence
- Approximates 25-delta via fixed moneyness (0.95/1.05) — could improve with delta calc
- Filters: volume > 10 or OI > 100 per leg, min 5 contracts each side
- Cron-friendly: single run fetches all tickers, updates history, outputs signals

## Next Steps

1. ✅ Create main.py, ic_analysis.py, notes.md
2. 🔄 Run daily via cron to accumulate history
3. ⏳ After 30 days: run IC analysis, document results
4. ⏳ Test regime conditioning (VIX > 20 vs < 20)
5. ⏳ Compare with alpha_02 (skew level) — does momentum add orthogonal info?