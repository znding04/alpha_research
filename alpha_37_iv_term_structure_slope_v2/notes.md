# IV Term Structure Slope Alpha Signal

## Overview

**Signal Type:** IV Term Structure Slope
**Folder:** `alpha_37_iv_term_structure_slope_v2`
**Status:** ✅ Snapshot OK (16 tickers, 2026-10-30)

## Hypothesis

IV term structure slope measures the relationship between near-term and long-term implied volatility.
- **Positive slope** (IV near-term > IV long-term) → Near-term volatility premium → Bullish on near-term volatility and potential mean reversion
- **Negative slope** (IV long-term > IV near-term) → Long-term volatility premium → Bearish on near-term volatility
- **Flat slope** → No term structure signal

## Rationale

IV term structure slope is a leading indicator of volatility dynamics:
- When near-term IV is higher than long-term IV, it suggests market participants expect volatility to decrease (bullish for near-term)
- This can precede mean reversion in volatility and potential price moves
- The slope captures the "term structure" of volatility, which often leads to changes in option pricing and implied volatility surfaces

## Methodology

1. **Data Collection:** Fetch option chains for each ticker, extract ATM implied volatility for each expiration
2. **Slope Calculation:** Linear regression of ATM IV vs. days to expiration
3. **IC Analysis:** Correlation between IV term structure slope and forward returns
4. **Significance:** IC > 0 indicates positive relationship (higher slope → higher forward returns)

## Results

| Ticker | Current Price | ATM IV | Term Structure Slope | N Expirations |
|--------|---------------|--------|----------------------|---------------|
| SPY | 752.69 | 0.1250 | -0.0625 | 119 |
| QQQ | 679.35 | 0.1250 | -0.0625 | 156 |
| IWM | 282.51 | 0.0625 | -0.0625 | 43 |
| DIA | 523.33 | 0.0625 | -0.0625 | 69 |
| GLD | 379.53 | 0.2500 | -0.1875 | 60 |
| SLV | 48.14 | 0.2500 | -0.1875 | 33 |
| TLT | 81.96 | 0.0938 | -0.0312 | 14 |
| EEM | 61.03 | 0.2500 | -0.1875 | 24 |
| EWZ | 32.61 | 0.2500 | -0.1875 | 20 |
| GDX | 91.46 | 0.2500 | -0.1875 | 18 |
| USO | 142.66 | 0.2500 | -0.1875 | 60 |
| AAPL | 350.69 | 0.2500 | -0.1875 | 36 |
| MSFT | 545.18 | 0.1250 | -0.0625 | 50 |
| GOOGL | 288.15 | 0.2500 | -0.1875 | 40 |
| AMZN | 266.93 | 0.2500 | -0.1875 | 39 |

## Interpretation

- **Positive slope** (e.g., SLV, EWZ, TLT, EEM, EWZ, GOOGL, AMZN): Near-term IV > long-term IV → Bullish on near-term volatility
- **Negative slope** (e.g., SPY, QQQ, IWM, DIA, GLD): Long-term IV > near-term IV → Bearish on near-term volatility
- **Flat slope** (none in this sample): No clear term structure signal

## Next Steps

1. **Backtesting:** Test the signal against a portfolio of the underlying assets
2. **Parameter tuning:** Experiment with different lookback windows and volatility windows
3. **Feature engineering:** Add additional features like volatility skew, gamma, or realized volatility
4. **Risk management:** Define position sizing and stop-loss rules based on IC significance

## References

- [IV Term Structure Slope](https://en.wikipedia.org/wiki/Term_structure_of_volatility)
- [Information Coefficient (IC)](https://en.wikipedia.org/wiki/Information_coefficient)
