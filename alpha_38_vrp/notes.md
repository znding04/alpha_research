# VRP (Variance Risk Premium) Alpha Signal

## Overview

**Signal Type:** VRP (Variance Risk Premium)  
**Folder:** `alpha_38_vrp/`  
**Data Source:** yfinance option chains + daily price history

## Hypothesis

The Variance Risk Premium (VRP = IV² − RV²) predicts forward equity returns. When implied volatility is high relative to realized volatility (positive VRP), options are overpriced and forward returns tend to be lower (complacency → subsequent sell-off). When IV is low relative to RV (negative VRP), options are underpriced and forward returns tend to be higher (fear → subsequent rebound).

Cross-sectionally: rank tickers by VRP. Most positive = most complacent (overpriced vol, avoid/short). Most negative = most fearful (underpriced vol, overweight).

## Rationale

- **IV²** represents the market's expectation of future variance (priced in option premiums)
- **RV²** represents the actual realized variance (computed from historical price movements)
- VRP measures the gap between expected and realized variance
- Historically, VRP > 0 in equities — investors pay a premium for downside protection (put buying)
- Mean-reversion: extreme VRP values tend to revert toward zero as vol expectations adjust
- Cross-sectional dispersion: the relative VRP ranking across tickers identifies which names have most/least expensive vol

## Methodology

1. **IV Collection:** For each ticker, fetch option chain for expiration closest to 30 DTE (±10 days window)
2. **ATM IV:** Median implied volatility of strikes within ±2% moneyness with IV > 5%
3. **Realized Vol:** 30-day annualized realized volatility from daily close-to-close log returns
4. **VRP:** VRP = IV² − RV²
5. **Cross-Sectional Rank:** Rank all 16 tickers by VRP value
6. **IC Test:** Correlation between VRP signal and 5-day forward returns

## Results

### Live Snapshot (2026-11-12)

Run `python3 alpha_38_vrp/main.py` to regenerate.

| Metric | Value |
|--------|-------|
| Tickers analyzed | 16 (SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO, AAPL, MSFT, GOOGL, AMZN) |
| Data source | yfinance option chains (free) |
| Output file | `data/vrp_latest.csv` |

### Interpretation

- **VRP > 0** → IV² > RV² → vol overpriced → bearish forward return signal
- **VRP < 0** → IV² < RV² → vol underpriced → bullish forward return signal

### Notes

- IV is extracted from ATM options (closest to 30 DTE) to match the 30-day RV window
- Volume/OI filters applied for liquidity: volume > 10 OR openInterest > 100
- IV clipped to [0.01, 3.0] to exclude stale bids/asks
- Fixes numpy int64 comparison issue with `.fillna(0).replace([np.inf, -np.inf], 0).astype(int)` pattern

## Next Steps

1. Collect daily snapshots to build time-series IC
2. Run `alpha_38_vrp/ic_analysis.py` for forward-return IC test
3. Consider adding validation.py for pre-registered tradability test
