# VRP Skew Alpha Signal

## Hypothesis

**Variance Risk Premium (VRP) asymmetry between puts and calls contains predictive information for cross-sectional equity returns.**

- **VRP = IV² - RV²** (implied variance minus realized variance)
- **Put VRP** uses OTM put IV (~5% OTM); **Call VRP** uses OTM call IV (~5% OTM)
- **VRP Skew = Put VRP - Call VRP**
  - Positive VRP skew → puts are richer vs. calls relative to realized vol (crash hedging demand)
  - Negative VRP skew → calls are richer vs. puts (upside speculation / call overwriting)

**Prediction**: High VRP skew (expensive puts relative to calls) predicts *lower* forward returns (overpriced downside protection). Low/negative VRP skew predicts *higher* forward returns.

This is distinct from:
- Standard VRP (IV² - RV² at ATM) → equity premium
- IV Skew (Put IV - Call IV) → tail risk pricing
- VRP Skew isolates the *variance premium asymmetry* after controlling for realized vol level

## Theoretical Rationale

1. **Dealer hedging**: Market makers delta-hedge sold puts → sell futures when market drops → amplifies downside. Expensive put VRP reflects this structural demand.

2. **Insurance premium**: Investors systematically overpay for downside protection (put VRP > call VRP on average). When put VRP is *especially* high, it signals peak fear / oversold conditions.

3. **Call overwriting**: Systematic call selling (covered calls) suppresses call VRP. When call VRP > put VRP (negative skew), it signals complacency / yield-seeking.

4. **Information asymmetry**: Informed traders may express directional views via OTM options. Put VRP premium could reflect informed bearish flow.

## Signal Construction

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Universe | AAPL, SPY, QQQ, MSFT, GOOGL, AMZN | Liquid large-cap + index ETFs |
| RV lookback | 30 days | Standard monthly realized vol |
| OTM moneyness | 5% | Balance liquidity vs. skew sensitivity |
| Max DTE | 45 days | Focus on near-term where VRP is most stable |
| Aggregation | Mean across expirations | Reduce noise from single expiry |
| Frequency | Daily | Option chains update daily |

**Output**: Cross-sectional rank of `mean_vrp_skew` across tickers each day.

## Expected Decay

- **Horizon**: 5-10 days (VRP mean-reversion timescale)
- **Half-life**: ~10-15 days (based on VRP term structure literature)
- **Turnover**: Moderate (skew changes gradually unless event-driven)

## Look-Ahead Risks

1. **RV calculation**: Using trailing 30-day RV introduces look-ahead if not lagged properly. Must use RV up to *t-1* for signal at *t*.

2. **Option chain timing**: yfinance provides current chain only. Historical backtest requires stored daily snapshots.

3. **Earnings/events**: VRP skew spikes around earnings. Must flag/event-adjust or exclude.

## Preliminary Results (Current Snapshot, 2026-10-15)

| Ticker | RV | Near Put VRP | Near Call VRP | Near VRP Skew | Mean VRP Skew |
|--------|-----|--------------|---------------|---------------|---------------|
| SPY | 0.099 | 0.0058 | -0.0059 | **+0.0117** | +0.0011 |
| MSFT | 0.227 | -0.0358 | -0.0475 | **+0.0117** | +0.0021 |
| AMZN | 0.263 | -0.0534 | -0.0534 | 0.0000 | +0.0007 |
| AAPL | 0.204 | -0.0258 | -0.0258 | 0.0000 | +0.0004 |
| GOOGL | 0.230 | -0.0373 | -0.0373 | 0.0000 | +0.0004 |
| QQQ | 0.155 | -0.0200 | -0.0200 | 0.0000 | 0.0000 |

**Observations**:
- SPY and MSFT show positive VRP skew (put VRP > call VRP) — consistent with index/large-cap put protection demand
- Single-stock names (AAPL, GOOGL, AMZN, QQQ) show near-zero skew at nearest expiry
- Mean skew across expiries is small but positive for all names

## Next Steps

1. **Collect historical data**: Store daily option chain snapshots for true backtest
2. **Run IC analysis**: Cross-sectional IC vs. 5-day forward returns (need 6+ months history)
3. **Test event windows**: Exclude earnings weeks; test FOMC/CPI days separately
4. **Compare baselines**: IV skew, ATM VRP, put/call OI ratio
5. **Portfolio construction**: Long-short quintile spread, check transaction costs

## Related Literature

- Bollerslev, Tauchen, Zhou (2009) — "Expected Stock Returns and Variance Risk Premia"
- Doran, Ronn (2008) — "Computing the Market Price of Volatility Risk"
- Kilic, Shaliastovich (2019) — "Good and Bad Variance Premia and Expected Returns"
- Recent: VRP term structure (alpha_06), VRP momentum (alpha_18)

## Files

- `main.py` — Signal computation (current snapshot)
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This document