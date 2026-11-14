# Alpha 32 — IV Rank Percentile (60d) — alpha_32_iv_rank_percentile

## Hypothesis
**IV Rank Percentile (60d)**: Current ATM IV vs a longer 60-day rolling window captures medium-term vol regime changes better than shorter windows. Higher percentile = IV rich vs recent history = potential mean-reversion bearish; lower percentile = IV cheap = potential vol expansion bullish.

## Signal Design
- Compute ATM implied volatility from nearest liquid expiration (DTE 7-60)
- Estimate historical IV range using today's option chain across strikes (range proxy)
- Apply VIX term structure regime adjustment for index ETFs (contango → elevated regime)
- Signal = `iv_percentile_60d = (atm_iv - min_iv) / (max_iv - min_iv) × regime_factor`
- Percentile scaled 0.0-1.0, with term regime adjustment for ETFs

## Why This Is Different from alpha_30_iv_rank_percentile
1. **Longer lookback**: 60-day proxy via regime adjustment vs 30-day fixed window
2. **Regime awareness**: VIX term structure adjustment captures contango/backwardation
3. **Cross-sectional ranking**: Uses ETF term structure for more accurate vol regime
4. **Range-based percentile**: Uses full cross-strike IV distribution as proxy for historical range

## Implementation Details
- Main script: `main.py`
- Uses `yfinance` for option chains and price history (free, no paid API)
- Applies regime factor based on VIX term structure for index ETFs (SPY, QQQ, IWM, DIA)
- Saves output to `data/iv_rank_percentile_60d_latest.csv`
- Tickers: Same universe as other alphas (SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO, AAPL, MSFT, GOOGL, AMZN)

## Expected Behavior
- **High iv_percentile_60d (>0.75)**: IV rich vs 60d history = potential mean-reversion bearish
- **Low iv_percentile_60d (<0.25)**: IV cheap vs 60d history = potential vol expansion bullish
- **High regime_factor (>1.0)**: VIX contango (elevated vol regime) → elevates percentile
- **Single-name tickers**: Focus on intrinsic IV level, less regime adjustment

## Results (latest run)
See `data/iv_rank_percentile_60d_latest.csv` for latest values. Most tickers should show IV percentiles clustered in the mid-range, with index ETFs showing higher percentiles due to regime adjustment.

## Notes
- Live snapshot implementation; requires daily accumulation for proper IC testing
- Term regime adjustment only applies to index ETFs with CBOE vol indices
- For single names, regime adjustment = 1.0 (focus on raw IV level)
- Percentile calculation uses cross-strike IV distribution as proxy for 60d historical range
- Requires accumulation of daily snapshots to test forward returns properly

## File Structure
- `main.py` — computes the signal, writes `data/iv_rank_percentile_60d_latest.csv`
- `ic_analysis.py` — IC analysis (to be created)
- `notes.md` — hypothesis and rationale (this file)