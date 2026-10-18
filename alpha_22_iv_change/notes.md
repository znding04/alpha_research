---
title: "IV Change (Contrarian Mean-Reversion Signal)"
level: intermediate
topic: alpha-signal
order: 22
---

# IV Change — Contrarian Mean-Reversion Signal

## Hypothesis

When near-term ATM implied volatility (IV) has fallen sharply over the past 5 trading days (compression), the market has likely priced in a calm period that may reverse. Conversely, sharp rises in IV (fear spikes) tend to overshoot realized outcomes. Tracking the cross-sectional 5-day change in near-term ATM IV produces a contrarian signal: tickers with the largest recent IV drops rank highest (expected positive forward return), while tickers with rising IV rank lowest.

This is a pure time-series / cross-sectional hybrid: we need a time-series of IV snapshots to compute the change, but the ranking is cross-sectional at each snapshot date.

## Signal Design

- **Data**: yfinance option chain for each ticker (nearest expiration with DTE 14–60 days).
- **ATM IV**: median implied volatility of liquid contracts within ±5% of current spot price.
- **Prior snapshot**: cached in `alpha_22_iv_change/data/iv_history.csv` from the previous run.
- **IV Change (5d)**: `current_atm_iv - prior_atm_iv`.
- **Rank signal**: negative of the change (`-iv_change_5d`), so large drops = higher rank.

## Key Edge Cases

- **First run / missing history**: no prior snapshot exists, so `iv_change_5d = 0.0` and `prior_atm_iv = current_atm_iv`. The first meaningful signal requires at least two snapshots (one to establish a baseline, one to measure change).
- **Synthetic placeholder for first run**: the snapshot is saved to the history file; the next run will use the saved value as `prior`.
- **Expiration change**: different expirations may be selected between runs (DTE varies), which introduces noise; using a fixed DTE window (14–60) minimizes this.

## Expected Behavior

- **Positive correlation with forward returns for the contrarian rank**: compression (negative change) → positive forward return. The IC should be positive if mean-reversion holds.
- **Decay**: IV changes are short-lived (mean-reversion half-life ~5–15 days); signal value decays quickly, requiring frequent (daily) snapshots.
- **Vol-of-vol interaction**: this signal pairs well with `alpha_11_vol_of_vol` (regime stability) — high vol-of-vol + compression = stronger contrarian signal.

## Status

- ✅ Snapshot computation complete for all 6 tickers.
- ⚠️ Requires ≥2 daily snapshots before `iv_change_5d` is meaningful (first snapshot writes baseline; second snapshot produces first real change).
- ⚠️ Historical data is synthetic / single-run only; multi-day rolling history needs accumulation.
- 🔄 IC testing requires pooled daily snapshots (≥30 days) for statistical significance.

## References

- Black (1975): "Fact and Fantasy in the Use of Options" — original variance risk premium observation.
- Bollerslev & Zhou (2006): "Volatility Puzzles" — IV dynamics and mean-reversion patterns.
