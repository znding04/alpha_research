# Alpha 33 — VRP (Variance Risk Premium), cross-sectional 6-ticker

## Hypothesis
The variance risk premium (VRP = IV² − RV²) measures how much more expensive
options are than realized variance. Positive VRP = option sellers collect a
volatility risk premium → cross-sectionally, tickers with richer options
(higher VRP) should exhibit higher forward returns as the premium decays.

## Signal Design
- ATM IV from nearest liquid expiration (14–60 DTE), volume/OI-weighted
- 30-day realized volatility from yfinance daily price history
- Signal: `vrp_variance = atm_iv² − realized_vol²`, cross-sectionally ranked
- Universe: AAPL, SPY, QQQ, MSFT, GOOGL, AMZN (6 tickers, cross-section only)

## Why This Works (Expected)
- VRP is a classic, well-documented equity risk premium (options are
  systematically expensive vs realized vol; selling vol earns carry)
- Cross-sectionally, high-VRP names carry more vol risk premium
- Predictive horizon: 1–5 trading days

## Implementation Details
- `main.py` — computes latest VRP for each of 6 tickers; writes
  `data/vrp_alpha_33_latest.csv`
- `ic_analysis.py` — cross-sectional IC vs 5-day forward returns
- Uses yfinance only (free); no paid APIs
- Cross-sectional rank output for immediate signal ranking

## Results (latest run)
VRP variance per ticker + cross-sectional rank saved to CSV. Full IC requires
accumulated daily snapshots (≥30 obs per compute_ic minimum).

## Validation Design
**Pre-registration:** Future validation will test:
1. In-sample (≤2018) IC of VRP vs next 5-day return on the 6-name universe
2. Out-of-sample (2019–2026) IC with sign as hypothesized
3. Hedge-relevant IC against delta-hedged 30-day ATM straddle returns
4. Break-even cost analysis (straddle round-trip cost vs gross alpha)

## Related Signals
- alpha_04_vrp: VRP (IV² − RV²), full 16-ticker universe
- alpha_21_vrp: Day-over-day VRP change
- alpha_23_vrp: VRP refined (30d RV, cross-section rank, 16 tickers)
- alpha_20_vrp_skew: Put VRP minus Call VRP asymmetry

This signal is a clean cross-sectional VRP on the constrained 6-ticker universe
with vol-points output and cross-sectional ranking.
