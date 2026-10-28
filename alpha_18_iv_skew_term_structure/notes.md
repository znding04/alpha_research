# IV Skew-Term Structure Signal (alpha_18)

## Hypothesis
Combining IV term structure slope with skew term structure slope provides a stronger mean-reversion signal than either component alone.

- **IV term structure slope** (short-term IV minus long-term IV): Upward-sloping term structure (long > short) often signals mean reversion — long-dated IV is "expensive" relative to short-dated, suggesting overpriced tail risk.
- **Skew term structure slope** (long-dated skew minus short-dated skew): Increasing skew over time (more negative put IV relative to calls) signals growing downside hedging demand.

When both align (upward IV slope + increasing skew), the signal suggests:
- Long-dated options are relatively overpriced (both in level and skew)
- Mean reversion trade: sell long-dated / buy short-dated structure
- Cross-sectional signal: assets with strongest alignment should underperform

## Signal Construction

```
IV_slope = IV(75d) - IV(30d)          # positive = upward term structure
Skew_slope = Skew(75d) - Skew(30d)    # positive = skew increases with tenor

IV_slope_signal = -IV_slope           # negative = mean reversion BUY
Skew_slope_signal = Skew_slope        # positive = bearish skew signal

Combined_signal = 0.4 * IV_slope_signal + 0.6 * Skew_slope_signal
Signal_strength = Combined_signal / 0.02  # normalized
```

## Data Source
- yfinance option chains
- Two expirations: ~30 DTE and ~75 DTE
- Liquid contracts only (volume > 10 or OI > 100, IV > 0.01, IV < 3.0)

## Expected Performance
- Cross-sectional: Signal should predict next 21-day returns
- Time-series (SPY): Mean reversion on term structure extremes
- Historical IC target: |IC| > 0.05, t-stat > 2

## Related Signals
- alpha_02_iv_skew_dynamics: Pure skew (no term structure)
- alpha_03_iv_term_structure: Pure IV term structure (no skew)
- alpha_25_iv_term_structure_slope: Calendar spread focus

## Status
- [x] main.py (live snapshot)
- [x] ic_analysis.py (framework)
- [ ] historical.py (needs CBOE vol index + skew history)
- [ ] validation.py (needs tradability test)

## Live Results (2026-10-28)
Most tickers show zero skew slope — the simplified delta approximation in main.py needs refinement.
GLD shows strong negative signal (-2.58): IV slope of +0.1292 with no skew slope.
This suggests long-dated GLD vol is significantly higher than short-dated (tail hedging in gold).
