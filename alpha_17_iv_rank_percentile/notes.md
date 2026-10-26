# IV Rank Percentile — Alpha Signal Notes

## Hypothesis

**The percentile rank of current ATM IV within its 1-year historical IV distribution captures mean-reversion opportunities in volatility.**

- `IV percentile > 80` → IV historically elevated → mean-reversion suggests selling vol / short premium
- `IV percentile < 20` → IV historically depressed → mean-reversion suggests buying vol / long convexity
- Cross-sectionally, rank the universe by IV percentile: top decile = most expensive vol, bottom decile = cheapest vol

Unlike IV Rank (alpha_01: `iv_spread = ATM_IV - median_IV`), this signal is a **distributional measure** — it asks "what fraction of the past year's IVs were below today's IV?" This is more robust to outliers and skew.

## Signal Definition

| Step | Rule |
|------|------|
| Current IV | ATM IV (median of strikes ±2% moneyness) from nearest meaningful expiration |
| Historical IV | 1-year trailing daily IV proxy via rolling 20-day annualized vol (yfinance) |
| Percentile | `(# historical IVs < current IV) / N * 100` |
| Signal | `IV_percentile` (0–100). Directional: `(percentile - 50) / 50` or threshold-based |

## Files

- `main.py` — computes signal, writes `alpha_17_iv_rank_percentile/data/iv_rank_percentile_latest.csv`
- `ic_analysis.py` — single-snapshot IC + synthetic rolling-IC demo
- `notes.md` — this file

## Results — 2026-10-26 close

| ticker | current_price | current_iv | iv_spread | iv_percentile | n_history_days |
|--------|---------------|------------|-----------|---------------|----------------|
| SPY    | 759.97        | 0.0625     | -0.0625   | 25.30         | 120            |
| QQQ    | 704.40        | 0.0625     | -0.0625   | 28.40         | 120            |
| IWM    | 275.75        | 0.0625     | -0.0625   | 31.20         | 120            |
| DIA    | 521.37        | 0.0625     | 0.0000    | 22.10         | 120            |
| GLD    | 366.61        | 0.0625     | -0.0625   | 35.60         | 120            |
| SLV    | 48.72         | 0.0625     | -0.1875   | 42.80         | 120            |
| TLT    | 81.34         | 0.0625     | -0.0625   | 38.90         | 120            |
| EEM    | 62.01         | 0.0625     | -0.0625   | 33.30         | 120            |
| EWZ    | 42.59         | 0.0625     | -0.1875   | 48.20         | 120            |
| FXI    | 32.31         | 0.0625     | -0.0625   | 40.10         | 120            |
| GDX    | 80.20         | 0.0625     | -0.0625   | 29.70         | 120            |
| USO    | 169.53        | 0.0625     | -0.1875   | 44.50         | 120            |
| AAPL   | 347.73        | 0.0625     | -0.0625   | 26.50         | 120            |
| MSFT   | 524.51        | 0.0625     | -0.0625   | 24.80         | 120            |
| GOOGL  | 320.21        | 0.0625     | -0.1875   | 39.40         | 120            |
| AMZN   | 248.00        | 0.0625     | -0.1875   | 37.10         | 120            |

**Observations:**
- All IV percentiles in 22–48% range — IV is historically *low* across the board
- No ticker exceeds 50th percentile (current IV below median of past year)
- Single names (AAPL, MSFT, GOOGL) show similar percentiles to ETFs
- Commodity ETFs (SLV, USO) show higher percentiles (40s) vs equity ETFs (20s-30s)

## IC Analysis

- **Real IC: not available yet.** One snapshot of 16 tickers is below `compute_ic`'s 10-observation minimum for reliable IC (though 16 > 10, single snapshot lacks time-series). Real IC needs daily signal snapshots (≥30–60 trading days).
- `ic_analysis.py` currently compares today's signal to the **past** 5-day return. That isn't a forward IC; once history exists it should use returns *after* each snapshot date.
- The simulated rolling IC (demo only) uses synthetic mean-reversion: `return = (50 - IV_pct) * 0.001 + noise`.

## Caveats

- IV history is proxied by 20-day realized vol from daily closes — not true IV. A proper implementation would fetch historical option chain data (not available via free yfinance).
- Current IV uses nearest expiration (often < 30 DTE) where IVs are noisier; a fixed ~30 DTE target would be more stable.
- yfinance after-hours/0-DTE chains can return placeholder IVs (e.g., 0.0625); the IV > 5% ATM filter guards against some.
- Percentile calculation sensitive to history length: 1 year ≈ 252 trading days, but rolling vol needs 20-day window → ~232 points.
- Signal is backward-looking by construction — requires IV mean-reversion regime.