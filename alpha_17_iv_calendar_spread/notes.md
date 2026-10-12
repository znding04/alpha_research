# IV Calendar Spread Alpha Signal — Notes

## Hypothesis

**Calendar spread IV differentials (short-term ATM IV minus long-term ATM IV) predict forward equity returns and volatility convergence.**

### Rationale

1. **Term Structure Information**: The IV term structure reflects market expectations of future volatility. When near-term IV exceeds far-term IV (backwardation), it signals elevated near-term uncertainty/hedging demand. When far-term IV exceeds near-term IV (contango), it reflects complacency or expected future volatility.

2. **Mean Reversion**: Calendar spreads are delta-neutral strategies that isolate pure term structure dynamics. Extreme calendar spreads (both backwardation and contango) tend to mean-revert as:
   - Near-term events resolve (earnings, FOMC, etc.) → IV crush
   - Long-term uncertainty gets priced in over time
   - Arbitrageurs exploit persistent mispricing

3. **Cross-Sectional Signal**: Across our universe (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN), the *relative* calendar spread ranking should predict cross-sectional returns. Stocks with most extreme backwardation (high short IV vs long IV) may underperform as near-term fear is overpriced; stocks in deep contango may outperform as complacency unwinds.

## Signal Definition

| Component | Description |
|-----------|-------------|
| **Primary Signal** | `cal_spread_vol = IV(short_dte) - IV(long_dte)` at ATM |
| **Variance Space** | `cal_spread_var = IV(short)² - IV(long)²` (economically meaningful for VRP) |
| **Normalized** | `cal_spread_pct = cal_spread_vol / IV(long)` |
| **Slope** | `slope_per_day = cal_spread_vol / (long_dte - short_dte)` |
| **Regime** | BACKWARDATION (>2 vol pts), CONTANGO (<-2 vol pts), FLAT |

Default parameters: `short_dte=30`, `long_dte=60`

## Expected Predictive Power

| Horizon | Expected IC | Rationale |
|---------|-------------|-----------|
| 1-day | ~0.02-0.05 | Noise dominant, but extreme spreads may show immediate reversion |
| 5-day | ~0.05-0.10 | Event resolution (earnings, macro) drives IV convergence |
| 10-day | ~0.05-0.10 | Term structure roll-down becomes measurable |
| 20-day | ~0.03-0.08 | Mean reversion of volatility term structure |

## Look-Ahead Bias Prevention

- **Forward Returns Only**: Use t+1 to t+N returns, never current or past returns
- **Signal Lag**: Signal computed at market close, applied to next day's open
- **No Peeking**: Expiration selection based on DTE at signal time, not optimal hindsight
- **Liquidity Filters**: Volume/OI thresholds applied at signal time only

## Data Requirements

### Current (Live)
- yfinance option chains for 6 tickers
- Current spot prices
- Available expirations within 180 DTE

### Historical (For Backtest)
- Historical option chains (not available via yfinance)
- **Alternative**: Use CBOE historical data, OR calculate from historical VIX term structure as proxy
- **Minimum viable**: Daily snapshots of ATM IV by DTE for each ticker

## Implementation Status

- ✅ `main.py` — Live signal computation with liquidity filters
- 🔄 `ic_analysis.py` — Framework ready, needs historical data
- 📝 `notes.md` — This file

## Next Steps

1. **Historical Data**: Source historical option data (CBOE, ORATS, or vendor) to build signals_df
2. **Backtest**: Run rolling IC analysis with 60-day windows
3. **Optimize**: Test different DTE pairs (14/30, 30/60, 60/90, 30/90)
4. **Regime Conditioning**: Test if signal works better in high/low VIX regimes
5. **Combination**: Test calendar spread + IV rank + VRP as composite signal

## Related Signals

| Signal | Folder | Relationship |
|--------|--------|--------------|
| IV Term Structure Slope | `alpha_03_iv_term_structure/` | Similar but uses all expirations, not just 2 |
| VRP Term Structure | `alpha_06_vrp_term_structure/` | Uses variance space (IV²-RV²), we use raw IV |
| VRP Carry | `alpha_10_vrp_carry/` | Similar concept but variance space + realized vol |
| IV Term Momentum | `alpha_15_iv_term_momentum/` | Rate of change of term structure slope |

## Differentiation

This signal is **distinct** because:
- Pure IV calendar spread (no realized vol dependency)
- Delta-neutral by construction (ATM vs ATM)
- Only 2 expirations — clean, interpretable, tradable
- Directly maps to calendar spread trading strategy
- Can be combined with skew signals for surface-aware view

## Risk Factors

1. **Earnings Contamination**: Near-term IV inflated by earnings → filter earnings dates
2. **Liquidity Mismatch**: Short-dated options less liquid → widen filters
3. **Dividend Effects**: Early exercise premium on calls → use puts only or adjust
4. **Weekend/Expiry Effects**: IV behavior near expiry → skip DTE < 5
5. **Model Risk**: yfinance IV may differ from broker/market data

## Files Created

```
/alpha_17_iv_calendar_spread/
├── main.py           # Signal computation (live)
├── ic_analysis.py    # IC framework (needs historical data)
└── notes.md          # This file
```

## Commit Message

```
feat(alpha_17): add IV Calendar Spread alpha signal

- Computes ATM IV spread between 30d and 60d expirations
- Backwardation/contango/flat regime classification
- Delta-neutral, variance-space and vol-space metrics
- IC analysis framework ready for historical data
```