# Alpha 39 — VRP with EWMA-vol Forecast

## Hypothesis
The classic Variance Risk Premium (VRP = IV² − RV²) is a reliable cross-sectional
volatility-premium signal: when IV² > RV², vol is expensively priced (expected short-vol /
underweight); when IV² < RV², vol is cheap (expected long/overweight).

Existing VRP variants in this repo (alpha_04, alpha_20, alpha_21, alpha_23, alpha_30,
alpha_33, alpha_34, alpha_36, alpha_38) all use a **fixed trailing realized-vol window**
(30–60 days) as RV. That window mixes last-month realized vol with today's ATM IV,
inducing regime-lagged noise: the RV number reflects vol from up to 60 days ago,
while IV reflects today's forward vol expectation.

Alpha 39 replaces the fixed trailing RV with an **EWMA (RiskMetrics λ=0.94) forecast**
of next ~30-day realized vol. EWMA weights recent observations much more heavily
(effective half-life ≈ 6.2 trading days), so E[RV_ewma] is a forward-looking
realized-vol expectation much closer in time to today's ATM IV. This is a genuine
methodological upgrade on the same "IV² − RV²" question.

## Implementation
- **main.py**: fetches yfinance options chains, computes ATM IV via **Black-Scholes
  inversion from option-chain mid prices** (yfinance `impliedVolatility` is unreliable /
  stale in this environment; mid price ≈ (bid+ask)/2 with `lastPrice` fallback). Downloads
  6 months of daily closes, computes EWMA vol forecast, outputs `data/vrp_ewma_latest.csv`
  with columns: ticker, current_price, iv_atm, rv_ewma_30d, vrp, vrp_pct, n_contracts.
- **ic_analysis.py**: tests whether VRP_ewma predicts 5-day forward cross-sectional
  returns using `compute_ic()` from common.utils.
- Filters: liquidity via volume > 10 OR open interest > 100; positive `lastPrice`;
  expiration DTE ≤ 180, preferring DTE ≥ 7.
- EWMA forecast: alpha = 2 / (λ + 1) ≈ 0.0805 with λ=0.94; one-step-ahead variance
  V_{t+1} = (1−α)V_t + α·r_t²; annualized by √252.

## Results (2026-11-13 snapshot, 16 tickers)
- ATM IV range: 0.15 (TLT) – 0.54 (GDX)
- EWMA-RV range: ~0.00 (AAPL, MSFT implied near-zero realized vol in window) – 0.64 (GDX)
- VRP > 0 (expensive vol / short-vol): SPY, QQQ, DIA, EEM, FXI, USO, AAPL, MSFT, GOOGL, AMZN
- VRP < 0 (cheap vol / long): IWM, GLD, SLV, TLT, EWZ, GDX

Notably: GOOGL (IV 0.453 vs EWMA-RV 0.279) and AMZN (IV 0.432 vs EWMA-RV 0.040) show
sharp expensive-vol readings; GDX/GLD show strongly cheap vol readings consistent with
a gold-rally vol expansion where EWMA captures realized moves the option chain has already
partially priced.

## IC
Forward returns are not available yet for today's snapshot. Run `python3 ic_analysis.py`
after 5 trading days have elapsed post-signal-date, or pool daily snapshots over time
(compute_ic needs ≥10 observations) to get a stable cross-sectional IC.

## Next Steps
- Run ic_analysis.py after ~5 trading days to get 5-day forward IC.
- Compare IC against trailing-window VRP variants (alpha_38_vrp) to confirm EWMA improvement.
- Consider adding VRP_ewma to the signal ensemble if IC clears the same tradability bar.
