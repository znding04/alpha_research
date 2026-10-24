# VRP (IV² - RV²) — Alpha Signal Notes

## Signal Folder
`alpha_23_vrp/`

## Hypothesis

The Variance Risk Premium (VRP) captures the systematic premium paid
for downside-protection (implied vol) relative to the actual price
movement experienced (realized vol). It is one of the best-studied
cross-sectional equity premium signals.

- **Positive VRP** (`IV² > RV²`): options trade at a premium over
  realized volatility → options expensive → sell vol / equity may be
  overpriced relative to risk. Historically predicts lower or flat
  forward returns (mean-reversion of IV).
- **Negative VRP** (`IV² < RV²`): options trade at a discount to
  realized vol → buy vol / equity may be underpriced.

Cross-sectionally: tickers with the highest VRP should see lower
future returns (mean-reversion of vol) or should have earned a premium
during the holding period. The classic literature finds a positive
premium (positive VRP predicts positive future returns) — the
"variance swap" view. A refined cross-section test on the current
equity-volatility surface clarifies whether the premium is priced
in or predictive.

## Signal Definition

|| Step | Rule |
||---|---|
|| ATM IV | Weighted-average IV of strikes within ±5% of spot, nearest liquid expiration within 14–60 DTE |
|| RV 30D | 30-day annualized realized vol from `yfinance` price history (`std(log_returns) * sqrt(252)`) |
|| VRP | `IV² - RV²` (annualized, decimal) |
|| Cross-section | Percentile rank within 6 tickers (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN) from live option chains |
|| Output | `data/vrp23_latest.csv` |

## Implementation Differences vs alpha_04_vrp

- `main.py` uses **30-day realized vol** (not 20d) for smoother RV estimates.
- Uses `tq.info.get('currentPrice')` for price instead of `tq.info['currentPrice']` which avoids KeyError.
- Adds cross-sectional rank (`vrp_rank`) and absolute-rank percentile for easier signal comparison.
- Keeps `compute_rv_30d()` within the same file for portability.
- No dependency on synthetic historical back-fills; runs purely from today's `yfinance` data.

## Results — 2026-10-24 Snapshot

Computed using `python3 alpha_23_vrp/main.py`.

Example output (full 6-ticker results in `data/vrp23_latest.csv`):

- Positive VRP (IV > RV): SPY, QQQ, MSFT often positive (options expensive relative to recent realized movement).
- Negative VRP: AMZN, AAPL often negative (high recent realized vol vs. option-implied vol).
- This direction is consistent with a mean-reverting vol regime: high realized vol in recent weeks pulls VRP negative.

## Forward-Return Testing

Run `python3 alpha_23_vrp/ic_analysis.py` to compare current VRP to
5-day forward returns. Note: a single live snapshot does not provide
enough observations for a meaningful IC (`compute_ic()` requires ≥10
observations). Real predictive power requires accumulated daily
snapshots from `data/vrp23_latest.csv` over 30–60 trading days, or
historical comparison via `run_historical.py`.

## Caveats

- **Live-only signal**: uses current option chain + recent 30-day price
  history. No free historical option-chain source exists; historical
  VRP can be approximated from `common/history.py` CBOE index data but
  the live implementation is deliberately separate.
- **Look-ahead risk**: `ic_analysis.py` uses `signal_as_of()` anchored to the
  last close on or before the snapshot date; `forward_return()`
  requires 5 future trading days to have completed. A fresh snapshot
  from today cannot have a completed 5-day forward return yet.
- **Cross-section size**: only 6 active tickers (`TICKERS`). Small-N
  cross-sections produce noisy rank correlations; a broader 12-ETF
  or 17-name historical universe (`HIST_TICKERS`) gives more stable
  IC estimates.
- **Price-source sensitivity**: `tq.info` sometimes returns stale or
  missing `currentPrice` during after-hours; the signal uses the
  nearest available price to avoid `None` values.
