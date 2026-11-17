# VRP-Range (Parkinson realized vol) — Alpha Signal Notes

## Hypothesis

**Replacing the close-to-close realized-vol benchmark inside the variance risk
premium with a range-based estimator makes the implied-minus-realized gap a
cleaner signal, because the RV side is measured with far less noise.**

### Rationale

1. **VRP is a difference of two variances.** `VRP = IV² − RV²`. The implied leg
   (IV²) is a smooth market quote; the realized leg (RV²) is an *estimate* built
   from a finite number of daily returns. Estimation error in RV² feeds straight
   into VRP and dilutes its cross-sectional signal.
2. **Close-to-close RV is inefficient.** Using only daily closes throws away the
   intraday high and low. The Parkinson (1980) estimator uses the high/low range
   and is roughly **5x more statistically efficient** than close-to-close for a
   given number of days — i.e. with the same 60 days of data it pins down the
   realized variance much more tightly.
3. **Range estimators are robust to the artifacts that hurt close-to-close.**
   Overnight gaps (earnings, macro prints) and split/dividend quote jumps inflate
   close-to-close variance. Parkinson uses only the intraday range and is largely
   immune to a gap between yesterday's close and today's open.
4. **Cross-sectional read.** Ranking the 6 focus names (AAPL, SPY, QQQ, MSFT,
   GOOGL, AMZN) by VRP_range isolates relative vol richness between instruments
   driven by the same macro factor.

## Signal Definition

| Step | Rule |
|------|------|
| ATM IV | Median IV of strikes within ±2% moneyness (IV > 5%) from nearest liquid expiration (14–90 DTE) |
| Parkinson RV² | `(1 / (4 ln 2)) · mean[ ln(H/L)² ]` over the last 60 trading days, × 252 |
| Garman-Klass RV² | `0.5·ln(H/L)² − (2 ln2 − 1)·ln(C/O)²` averaged, × 252 — robustness check |
| **VRP_range** | `ATM_IV² − RV_parkinson²` |
| VRP ratio | `VRP_range / RV_parkinson²` (normalized) |
| vrp_rank | Cross-sectional percentile over the 6 focus names (1 = richest vol) |

### Interpretation

- `VRP_range > 0` → options priced above range-realized vol (rich premium)
- `VRP_range < 0` → options cheap vs realized (stress / underpriced vol)
- Cross-sectionally: highest rank = most expensive vol, lowest = cheapest

## Why this is a distinct alpha (not a duplicate)

Every prior VRP alpha in this repo (01, 04, 21, 23, 33, 34, 38, 39, 41) measures
realized volatility **close-to-close**. `alpha_39` uses an EWMA forecast of
close-to-close RV; `alpha_41` uses trailing 252d close-to-close. `alpha_44`
changes the *estimator family* to an OHLC range estimator (Parkinson primary,
Garman-Klass robustness). The information set is different: intraday range
captures realized variance that close-to-close misses, so the two VRP series are
not collinear and can carry independent cross-sectional signal.

## Hypotheses to test

- **H1 (return prediction):** cross-sectional rank of VRP_range predicts forward
  equity returns over 5–21 days. Sign ambiguous ex-ante: rich vol (high VRP)
  could mean fear/premium-collection (bearish continuation) or mean-reversion
  setup (bullish). Let the IC decide.
- **H2 (vol prediction):** high VRP_range predicts a *fall* in forward realized
  vol (vol mean-reversion). Expected negative IC vs forward ΔRV — this is the
  more likely edge and is common to all VRP variants.

## Data Source & Limitations

**Source:** yfinance option chains (nearest expiration, 14–90 DTE) + yfinance
daily OHLC history (1y).

**Limitations:**

1. **yfinance IV placeholders.** After-hours / thin chains return a default
   `impliedVolatility = 0.0625`; the `IV > 0.01` / `IV > 0.05` guards reduce but
   cannot eliminate this. A closed-market snapshot (e.g. 02:00 ET cron run) will
   show degenerate IVs across many tickers — treat such snapshots as data-quality
   flagged, not as signal.
2. **Range artifacts.** yfinance H/L can include bad prints; the `H>0, L>0` guard
   is applied but range data is not scrubbed for outliers. Parkinson is chosen
   partly because it is less sensitive to close-to-open gaps than Garman-Klass.
3. **60d window.** Short enough to react to regime shifts, long enough to keep
   the range estimator's variance low with 30+ observations.
4. **Single snapshot.** A one-day cross-sectional IC over 6 names is noise
   (below `compute_ic`'s 10-observation minimum). Real IC needs ≥60 accumulated
   daily snapshots.

## Files

- `main.py` — computes Parkinson + Garman-Klass RV, VRP_range, writes `data/vrp_range_latest.csv`
- `ic_analysis.py` — single-snapshot cross-sectional IC, focus-subset IC, Garman-Klass robustness IC, forward-ΔRV IC, synthetic rolling-IC demo

## Next Steps

1. Accumulate daily snapshots via `collect_snapshots.py` so `data/snapshots/` grows.
2. Compute rolling IC once ≥60 trading days exist.
3. Compare VRP_range vs VRP_core (alpha_41) IC series for incremental information.
4. If cross-sectional IC is significant, pre-register a tradability test on
   delta-hedged straddles (see `run_validation.py`) before calling it an alpha.
