# alpha_50_iv_rank_percentile — IV Rank Percentile (cross-sectional)

## Hypothesis
Current ATM IV percentile vs 1-year historical range predicts forward 5-day returns.
- High percentile (IV expensive → short vol) → expected negative returns (mean reversion)
- Low percentile (IV cheap → long vol) → expected positive returns (mean reversion)
- Effect: IV has strong mean reversion; when vol is rich, it tends to fall → prices rise.
  When vol is cheap, it tends to rise → prices may fall (risk-off).

## Rationale
- IV Rank Percentile measures where current IV sits in its 1-year range.
- High values: options relatively expensive → market is short volatility → historically, realized vol tends to catch up (vol fall → price rise).
- Low values: options relatively cheap → market is long volatility → historically, realized vol tends to stay low → price pressure persists.
- Prior alphas (alpha_05, alpha_17) showed IC ~−0.01 t−0.6 and −0.01 t−0.6 respectively — borderline significance with 17-name cross-section. A focused 6-name cross-section with proper historical baseline may yield cleaner signal.

## Signal Description
- **iv_percentile_1y**: Current ATM IV percentile rank vs 1-year historical ATM IV range [0, 1]
  - >0.8: IV rich vs history (short-vol bias) 
  - <0.2: IV cheap vs history (long-vol bias)
  - 0.2–0.8: normal regime
- Computed from live option-chain ATM IV + accumulated daily snapshots in data/snapshots/
- Defaults to 0.5 when insufficient historical data

## Results

| Date | Signal Value | Forward Return | IC Contribution |
|------|-------------|---------------|-----------------|

*Insufficient snapshot history yet — first run seeded data/snapshots with default 0.5 percentiles. Future runs will accumulate daily snapshots and enable rolling IC analysis.*

## Next Steps
1. Run `python3 alpha_50_iv_rank_percentile/main.py` daily (cron) to accumulate snapshots
2. After 60+ daily snapshots, run `python3 alpha_50_iv_rank_percentile/ic_analysis.py` to compute rolling IC
3. Expected IC sign: negative (high pctl → forward returns negative, mean reversion)
4. Target: |IC| > 0.05 with |t| > 2 for significance

## Files
- `main.py` — Live ATM IV computation + 1Y percentile + snapshot persistence
- `ic_analysis.py` — IC vs forward returns test
- `notes.md` — This file
- `data/iv_rank_percentile_latest.csv` — Latest output (gitignored)
- `data/snapshots/YYYY-MM-DD/iv_rank_latest.csv` — Accumulated historical snapshots