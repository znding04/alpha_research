# IV Rank (ATM vs Median IV Spread) — Alpha Signal Notes

## Hypothesis

**The spread between ATM implied volatility and the median IV across all liquid strikes captures where option demand is concentrated, and that positioning predicts forward returns.**

- `iv_spread > 0` → ATM vol premium (demand for at-the-money convexity, event risk)
- `iv_spread < 0` → OTM vol premium (tail-hedge demand: wings priced richer than ATM)

Cross-sectionally, tickers with the most negative spread carry the heaviest tail-hedge demand.

## Signal Definition

| Step | Rule |
|------|------|
| Expiration | Nearest expiry within 180 DTE |
| Liquidity filter | `volume > 50` OR `openInterest > 500`; `0.01 < IV < 3.0`; `lastPrice > 0`; ≥10 contracts |
| ATM IV | Median IV of strikes within ±2% moneyness (IV > 5%); fallback = closest strike |
| Median IV | Median IV over all filtered calls + puts |
| Signal | `iv_spread = ATM_IV - median_IV` |

## Files

- `main.py` — computes the signal, writes `data/iv_rank_latest.csv`
- `ic_analysis.py` — single-snapshot IC + synthetic rolling-IC demo

## Results (2026-10-16 close)

| Ticker | Price | ATM IV | Median IV | IV Spread | Contracts |
|--------|-------|--------|-----------|-----------|-----------|
| AAPL | 343.46 | 0.2514 | 0.3149 | -0.0636 | 36 |
| SPY | 763.25 | 0.1528 | 0.2680 | -0.1151 | 193 |
| QQQ | 709.80 | 0.2266 | 0.3672 | -0.1406 | 183 |
| MSFT | 529.05 | 0.2559 | 0.3057 | -0.0498 | 43 |
| GOOGL | 340.59 | 0.3126 | 0.3593 | -0.0467 | 38 |
| AMZN | 250.00 | 0.2927 | 0.4258 | -0.1331 | 39 |

All six spreads are negative: OTM wings trade above ATM across the universe. The index ETFs (QQQ, SPY) and AMZN show the steepest wing premium.

## IC Analysis

- **Real IC: not available yet.** One snapshot of 6 tickers is below `compute_ic`'s 10-observation minimum, so the result is `nan`. Real IC needs daily signal snapshots (≥30–60 trading days).
- `ic_analysis.py` currently compares today's signal to the **past** 5-day return. That isn't a forward IC; once history exists it should use returns *after* each snapshot date.
- The simulated rolling IC (mean 0.357, IR 7.3) comes from synthetic data where returns are built as `0.25 × signal + noise`. It's a demo of the pipeline, **not evidence of predictive power**.

## Caveats

- Nearest expiry is often only a few DTE, where IVs are noisy; a fixed ~30 DTE target would be more stable.
- The median IV mixes calls and puts and depends on which strikes pass the liquidity filter, so the contract count (36 vs 193) changes the signal's meaning across tickers.
- yfinance after-hours/0-DTE chains can return placeholder IVs (e.g. 0.0156, 0.0625); the IV > 5% ATM filter guards against most of these.
