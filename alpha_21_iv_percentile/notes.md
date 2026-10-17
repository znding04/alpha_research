# IV Rank Percentile — Alpha Signal (alpha_21)

## Hypothesis

**IV Rank Percentile (current ATM IV vs. 1-year historical range) contains predictive information for forward equity returns.**

High percentile (IV expensive vs. history) → fear elevated → IV mean-reverts DOWN → equity bounce.
Low percentile (IV cheap vs. history) → complacency → IV expands UP → equity underperformance.

Cross-sectionally rank tickers by IV percentile: cheapest-vol tickers should outperform, most-expensive-vol should underperform.

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `iv_percentile` | % of last ~260 obs with IV ≤ current IV | 0-100, higher = IV more expensive |
| `iv_zscore` | (current IV - hist mean) / hist std | Std devs from historical mean |
| `iv_rank` | (current - min) / (max - min) | 0-1, sensitive to outliers |

## Data Requirements

- **Frequency**: Daily EOD option chains (yfinance)
- **Universe**: AAPL, SPY, QQQ, MSFT, GOOGL, AMZN
- **Expirations**: 14-60 DTE, near-term liquid
- **Strikes**: Near-ATM (±5% moneyness), liquidity-weighted IV
- **Lookback**: ~252 trading days stored in `data/iv_history.json`

## Files

- `main.py` — Computes IV percentile per ticker, updates persistent history, saves `data/iv_percentile_latest.csv`
- `ic_analysis.py` — IC testing of IV percentile vs forward returns
- `notes.md` — This file

## Interpretation

| IV Percentile | Regime | Signal |
|---------------|--------|--------|
| ≥ 80 | Fear / stress | Sell vol, expect equity mean reversion UP |
| 60-80 | Elevated | Slightly expensive vol |
| 40-60 | Neutral | No edge |
| 20-40 | Depressed | Slightly cheap vol |
| ≤ 20 | Complacency | Buy vol, expect equity underperformance |