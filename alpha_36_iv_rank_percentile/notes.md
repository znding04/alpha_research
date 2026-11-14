# Alpha 36 — IV Rank Percentile Signal

## Hypothesis

**The percentile of current ATM IV within the cross-strike IV distribution predicts future
volatility regimes / forward returns.** A high percentile means IV is relatively expensive
compared to the options quoted today (overpriced), while a low percentile means IV is cheap
(relatively undervalued), potentially implying future vol expansion (for low) or vol
mean-reversion from above (for high).

Cross-sectionally, tickers ranked at the top of the IV percentile may be prone to realized
volatility falling (vol premium / short vol opportunity); tickers at the bottom may be prone
to vol rising (mean-reversion / long vol).

## Rationale

- Classic IV Rank / percentile signals compare current IV to historical IV range (e.g.,
  percentile vs 1-year high/low).
- yfinance only exposes current option chains; no historical option IV snapshots. The
  cross-strike IV distribution within today's chain is therefore used as a proxy for a
  historical range.
- In production, daily option chain snapshots (e.g., via collect_snapshots.py) can be stored
  and used to compute true percentile rank over a rolling window (e.g., 60 days).

## Signal Definition

| Step | Rule |
|------|------|
| Expiration | Closest to 30 DTE, within 7-180 DTE |
| Liquidity filter | volume>0 OR OI>50; bid>0; 0.03 < IV < 3.0; calls >=5, puts >=5 |
| IV proxy | min/max IV over combined call+put chain |
| Percentile | (atm_iv - min_iv) / (max_iv - min_iv), capped [0,1] → ×100 for ranking |
| Signal | `iv_percentile` (0-100) |

## Files

- `main.py` — computes the percentile signal, writes `data/iv_rank_percentile_latest.csv`
- `ic_analysis.py` — single-snapshot IC + synthetic rolling-IC demo

## Results — 2026-11-09 snapshot

Generated via `python3 alpha_36_iv_rank_percentile/main.py`.

- All 16 tickers from `common.universe.TICKERS` processed.
- Median percentile ≈ 50 by construction (distribution is empirical over chain), so
  absolute values are only meaningful relative to the cross-strike spread for now.
- True historical percentile validation (rolling windows) pending snapshot collection.

## Caveats

- Proxy-based percentile is distribution-relative and not a true rolling historical percentile.
- Low contract counts on some ETF legs may drop thin chains (similar to alpha_01 liquidity filter).
- IC analysis uses forward returns (5-day) against current snapshot; small-sample cross-sectional IC
  is preliminary and synthetic rolling IC is a demo.
