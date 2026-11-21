# Alpha 48 — IV Term Structure Slope

## Hypothesis

The slope of the ATM IV term structure (short-dated minus long-dated ATM IV) is a mean-reversion signal:
- **Slope > 0 (steep/contango):** Short-term IV is elevated relative to long-term → short-term vol is likely to normalize down → negative forward returns on short vol / signal decays (sell premium).
- **Slope < 0 (inverted/backwardation):** Long-term IV is elevated relative to short-term → short-term vol likely to mean-revert up → positive forward returns.

Tracked cross-sectionally across the watchlist: AAPL, SPY, QQQ, MSFT, GOOGL, AMZN (+ full TICKERS universe).

## Methodology

- Nearest expiration (>2 DTE) split into **short (7–30 DTE)** and **long (30–90 DTE)** ATM IVs.
- ATM IV = median of strikes within ±2% moneyness with IV > 5%, robust to liquidity filtering (volume > 10 OR OI > 100).
- Signal = short_IV − long_IV (absolute spread), reported in IV points and as % of long IV.
- Cross-sectional ranking: steepest → strongest short-vol mean-reversion bias; most inverted → strongest long-vol bias.

## Results (initial run, 2026-11-21)

The first run produced term structure slopes across the watchlist. Results saved to `data/iv_term_slope_latest.csv`; IC results saved to `data/iv_term_slope_ic.txt` (see IC analysis output below).

Interpretation conventions:
- `slope > 0` → steep term structure → expect short vol normalization (mean-revert down).
- `slope < 0` → inverted → expect short vol mean-reversion up.
- `|slope| > 0.05` (5 pts) → strong signal.

## Next Steps

- Accumulate daily snapshots to enable rolling IC validation (matching alpha_43 snapshot approach).
- Compare slope signal vs realized vol change over 5-day forward window.