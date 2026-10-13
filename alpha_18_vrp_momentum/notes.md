# VRP Momentum (alpha_18_vrp_momentum)

## Hypothesis

The Variance Risk Premium (VRP = IV² - RV²) measures the premium investors pay for variance protection. When VRP changes rapidly across the term structure, it signals shifting fear/complacency dynamics:

- **VRP Momentum** (near-term VRP change): Rising near-term VRP = increasing demand for short-term protection = potential near-term mean reversion as hedging pressure peaks
- **VRP Term Structure Slope**: Steepening VRP curve = increasing term premium for variance = regime transition signal

The core idea: VRP is typically positive (IV > RV) as investors pay premium for crash protection. When VRP compresses or turns negative, it signals complacency. When VRP spikes, it signals fear. The *rate of change* of VRP (momentum) may be a stronger predictor than VRP level alone.

## Signal Construction

1. **Realized Volatility (RV)**: 20-day annualized standard deviation of daily returns
2. **Implied Volatility (IV)**: ATM IV from liquid options (7-45 DTE)
3. **VRP**: IV² - RV² (variance space, not vol space)
4. **VRP Momentum**: Near-term VRP - Mid-term VRP (change in VRP across term structure)
5. **VRP Term Slope**: (Far VRP - Near VRP) / (Far DTE - Near DTE)

## Expected Predictive Relationships

| Signal | Expected IC Sign | Rationale |
|--------|------------------|-----------|
| Near VRP | Negative | High VRP = fear premium = subsequent mean reversion up |
| VRP Momentum | Negative | Rising VRP = escalating fear = oversold bounce likely |
| VRP Term Slope | Positive | Steep curve = term premium = carry opportunity |

## Data Requirements

- Daily option chain snapshots (yfinance)
- Historical price data for RV (yfinance)
- Minimum: 2 expirations in 7-45 DTE range per ticker
- Universe: AAPL, SPY, QQQ, MSFT, GOOGL, AMZN

## Current Status

- ✅ `main.py`: Signal computation working
- ✅ `ic_analysis.py`: IC framework implemented
- 🔄 `data/vrp_momentum_latest.csv`: Single snapshot collected
- ⏳ Rolling IC: Requires daily runs to build time series

## Results (Preliminary)

From first run (2026-10-13):
- All tickers show negative VRP (IV < RV) — unusual, typically VRP > 0
- VRP Momentum = 0 for most (near = mid VRP) — single snapshot limitation
- IC = NaN (no cross-sectional variation in single snapshot)

## Next Steps

1. **Run daily** to accumulate time series in `data/vrp_momentum_history/`
2. **Build rolling IC** once ≥20 days of data available
3. **Test different horizons**: 1-day, 5-day, 10-day, 20-day forward returns
4. **Refine RV window**: Test 10d, 20d, 30d, 60d RV
5. **Add VRP z-score**: Normalize VRP by its rolling std for cross-sectional comparability

## Look-Ahead Bias Prevention

- Only use data available at signal computation time
- Forward returns computed from *next* day's close
- No peeking at future option chains or prices

## Related Signals

- `alpha_04_vrp/`: VRP level (IV² - RV²)
- `alpha_06_vrp_term_structure/`: VRP across expirations
- `alpha_10_vrp_carry/`: VRP carry/roll-down
- `alpha_12_iv_momentum/`: IV momentum (vol space, not variance)
- `alpha_13_iv_skew_momentum/`: Skew momentum

## Files

- `main.py` — Core signal computation
- `ic_analysis.py` — IC testing framework
- `notes.md` — This file