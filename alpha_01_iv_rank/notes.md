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

## Results — expanded ETF universe (2026-10-16 close)

Universe: 12 ETFs (SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO) + AAPL, MSFT, GOOGL, AMZN, from `common/universe.py`. Raw: `data/snapshots/2026-10-16/`.

| ticker | atm_iv | median_iv | iv_spread | n_contracts |
|---|---|---|---|---|
| SPY | 0.1528 | 0.2969 | -0.1440 | 223 |
| QQQ | 0.2266 | 0.4072 | -0.1806 | 207 |
| IWM | 0.1829 | 0.2500 | -0.0671 | 67 |
| DIA | 0.1580 | 0.1765 | -0.0185 | 102 |
| GLD | 0.1759 | 0.2285 | -0.0527 | 65 |
| SLV | 0.3296 | 0.5547 | -0.2251 | 54 |
| TLT | 0.1494 | 0.2422 | -0.0928 | 38 |
| EEM | 0.2979 | 0.3565 | -0.0586 | 36 |
| EWZ | 0.5347 | 0.6445 | -0.1099 | 51 |
| FXI | 0.3086 | 0.3428 | -0.0342 | 14 |
| GDX | 0.3772 | 0.4111 | -0.0339 | 20 |
| USO | 0.4851 | 0.5303 | -0.0452 | 69 |
| AAPL | 0.2514 | 0.5398 | -0.2884 | 69 |
| MSFT | 0.2559 | 0.3643 | -0.1084 | 65 |
| GOOGL | 0.3126 | 0.4316 | -0.1191 | 52 |
| AMZN | 0.2927 | 0.4961 | -0.2034 | 51 |

**ETF vs single-name observations:**
- Every name has negative spread (wings > ATM). Broad equity ETFs (SPY −0.144, QQQ −0.181) and SLV (−0.225) carry the steepest wing premium; DIA, FXI, GDX are nearly flat.
- Single names (AAPL −0.288, AMZN −0.203) look extreme partly because their median IV includes earnings-inflated contracts; ETFs have no earnings event, so their spread reflects pure smile shape.

## Results — original 6 tickers, old liquidity filter (2026-10-16 close)

*Superseded: computed with the old `volume > 50 or OI > 500` filter. Loosening it to the repo-standard `> 10 / > 100` admits more far-wing strikes into the median IV, which moves the spread a lot (AAPL −0.064 → −0.288). The signal is sensitive to the contract filter; a fixed moneyness band for the median would make it more robust.*

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
