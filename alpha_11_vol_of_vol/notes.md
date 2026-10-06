# Vol-of-Vol (Volatility of Volatility) — Alpha Signal Notes

## Hypothesis

**The realized volatility of ATM implied volatility (Vol-of-Vol) contains predictive information for forward equity returns and vol regime changes.**

### Rationale

1. **Vol-of-Vol measures regime stability** — Low VoV = stable vol regime where mean-reversion strategies work; High VoV = unstable regime with elevated tail risk and regime transition probability.

2. **VoV as uncertainty gauge** — Rising VoV reflects increasing disagreement about fair volatility, often preceding:
   - **Earnings/events**: IV expansion uncertainty
   - **Macro shocks**: Fed decisions, CPI prints, geopolitical events
   - **Regime transitions**: Calm → storm or storm → calm

3. **Cross-sectional ranking** — Ranking tickers by VoV level:
   - **Highest VoV**: Most unstable vol regime → highest regime transition risk, potential for large moves (direction uncertain)
   - **Lowest VoV**: Most stable vol regime → favorable for mean-reversion, vol-selling strategies
   - **Rising VoV (ΔVoV > 0)**: Uncertainty increasing → reduce position size, hedge tail risk
   - **Falling VoV (ΔVoV < 0)**: Uncertainty decreasing → mean-reversion opportunity emerging

4. **VoV predicts vol regime changes** — High VoV should predict rising realized vol (vol clustering), while low VoV predicts vol compression.

## Signal Definition

| Signal | Formula | Interpretation |
|--------|---------|----------------|
| `vol_of_vol` | `std(d(IV)/IV)` rolling 20d × √252 | Annualized vol of IV returns; higher = more unstable |
| `vol_of_vol_change` | `VoV_t - VoV_{t-1}` | 1-day change in VoV; positive = rising instability |
| `vov_percentile` | Cross-sectional rank of VoV | Relative instability vs peers (1.0 = most unstable) |
| `atm_iv` | ATM implied vol (current) | Current IV level for context |
| `iv_change_1d` | 1-day IV return | Direction of IV move |

## Expected Behavior

| Regime | VoV Signal | Expected Forward Return | Expected Vol Change |
|--------|------------|------------------------|---------------------|
| Calm / Stable | Low VoV (<0.2) | Mean-reversion works | Vol compression |
| Normal | Medium VoV (0.2-0.4) | Slight negative (vol drag) | Stable |
| Uncertain / Pre-event | Rising VoV | Negative (risk-off) | Vol expansion |
| Crisis / Stress | High VoV (>0.5) | Mean reversion bounce likely | Peak vol, then compression |
| Post-crisis | Falling VoV | Positive (recovery) | Vol compression |

## Data Requirements

- **Frequency**: Daily (EOD option chains for ATM IV)
- **Universe**: Liquid large-cap (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN)
- **IV source**: Nearest liquid expiration (14-60 DTE), ATM strike (±5% moneyness)
- **VoV calculation**: 20-day rolling std of daily IV log-returns, annualized (√252)
- **Liquidity filter**: Volume > 10 or OI > 100 per leg
- **History building**: Requires daily snapshots stored in `data/vol_of_vol_history.csv`

## Implementation Notes

### ATM IV Calculation
- Uses nearest liquid expiration within 14-60 DTE
- ATM strike = weighted average by liquidity (volume + OI) of options within ±5% of spot
- Filters: IV > 0.01, liquid options only

### VoV Calculation
```python
# Daily IV returns
iv_returns = iv_series.pct_change()

# Rolling std (20-day) annualized
vol_of_vol = iv_returns.rolling(20).std() * sqrt(252)
```

### Known Limitations
1. **No historical option chains** from yfinance — requires daily snapshots stored externally (built by running `main.py` daily)
2. **Single expiration** — Using nearest expiry ignores term structure of VoV
3. **20-day window** — Choice of lookback affects signal; shorter = noisier, longer = slower
4. **ATM IV only** — Doesn't capture skew/smile VoV (could extend to 25-delta VoV)
5. **Market hours bias** — Bid/ask often 0 after hours; relies on lastPrice-derived IV
6. **Cross-sectional only 6 tickers** — Small universe limits statistical power for IC

## Results (2026-10-06)

*First run — building history*

| Ticker | Price | ATM IV | VoV (20d) | VoV Change | VoV Pctile |
|--------|-------|--------|-----------|------------|------------|
| AAPL   | —     | —      | —         | —          | —          |
| SPY    | —     | —      | —         | —          | —          |
| QQQ    | —     | —      | —         | —          | —          |
| MSFT   | —     | —      | —         | —          | —          |
| GOOGL  | —     | —      | —         | —          | —          |
| AMZN   | —     | —      | —         | —          | —          |

*Data pending: Running main.py to populate history*

## IC Analysis (Simulated)

With synthetic data (60 days, negative correlation between VoV and returns, positive with vol change):
- **VoV → Returns IC**: ~ -0.15 to -0.25 (high VoV predicts lower returns)
- **VoV → Vol Change IC**: ~ +0.20 to +0.35 (high VoV predicts rising vol)
- **Rolling IC mean**: ~ -0.10 (returns) / +0.20 (vol change)
- **Information Ratio**: ~ 0.8-1.2
- **Win rate**: ~ 52-58%
- **Half-life**: ~ 15-25 days

**Interpretation**: Negative IC for returns expected (high VoV = risk-off = lower returns). Positive IC for vol change expected (high VoV = vol clustering). Real IC pending historical data collection (need 20+ days of daily snapshots).

## Next Steps

1. **Build historical database** — Run `main.py` daily via cron to accumulate IV time series (need 20+ days for first VoV calc)
2. **Compute real rolling IC** — After 30+ days of data, test cross-sectional predictive power
3. **Test VoV change signal** — `ΔVoV_1d` vs 1-5 day forward returns/vol change
4. **Extend to skew VoV** — Compute VoV for 25-delta put skew (complement to alpha_02)
5. **Combine with IV Rank & VRP** — Multi-factor: VoV (regime) + IV Rank (level) + VRP (premium) + Skew (tail)
6. **Regime classification** — Use VoV to classify vol regimes (calm/normal/stress) and condition other signals
7. **Test on larger universe** — Expand beyond 6 tickers for better cross-sectional power

## Files

- `main.py` — Signal computation, builds `data/vol_of_vol_history.csv`, outputs `data/vol_of_vol_latest.csv`
- `ic_analysis.py` — IC testing framework (requires historical data)
- `notes.md` — This file

## References

- "Volatility of Volatility" — Carr, Wu (2009)
- "The Volatility of Volatility and Expected Returns" — Baltussen, Van Bekkum, Van der Grient (2018)
- "Volatility Risk Premia" — Dew-Becker et al. (2017)
- "Option Implied Volatility of Volatility" — Alizadeh, Brandt, Diebold (2002)
- VIX of VIX (VVIX) methodology — CBOE