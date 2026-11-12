# Alpha 36 — VRP (Variance Risk Premium) Signal

## Hypothesis

**VRP = IV² − RV² captures the variance risk premium: when implied variance
exceeds realized variance, vol is expensive (IV^2 > RV^2). When implied variance
falls below realized variance, vol is cheap (IV^2 < RV^2) — potential mean-reversion.

Cross-sectionally: higher VRP indicates expensive vol (short/avoid), lower VRP
indicates cheap vol (overweight/long).

## Rationale

- VRP is a well-established concept: positive VRP historically associated with
  equity market periods where options were expensive, often coincident with lower
  forward equity returns (inverse risk premium) or higher expected returns
  (compensated for bearing vol risk).
- By ranking tickers by VRP, we can identify relative vol pricing and potential
  opportunities across the equity universe.
- Computation uses ATM IV from current option chain (30 DTE) and 30-day realized
  volatility (annualized) from daily close-to-close log returns. yfinance only,
  no paid APIs.

## Signal Definition

| Step | Rule |
|------|------|
| IV | ATM implied volatility from nearest expiration to 30 DTE (within ±10 DTE) |
| RV | 30-day annualized realized volatility from daily log returns |
| VRP | VRP = IV² − RV² (basis points of variance) |
| Signal | `vrp_bps` (basis points of variance; higher = expensive vol) |

## Files

- `main.py` — computes VRP, writes `data/vrp_latest.csv`
- `ic_analysis.py` — single-snapshot IC + synthetic rolling-IC demo

## Results — 2026-11-09 snapshot

Generated via `python3 alpha_36_vrp/main.py`.

- All 16 tickers from `common.universe.TICKERS` processed (as of 2026-11-09).
- VRP values range across the cross-section, reflecting relative IV vs RV differences
  among tickers.
- True historical VRP would require daily IV/RV time series; current snapshot provides
  a cross-sectional view of relative vol premium.

## Caveats

- IV sourced from current option chain (static snapshot). Real VRP would need daily
  IV (requires storing option chain snapshots) and daily RV (rolling).
- Realized volatility computed from last 30 trading days; results sensitive to market
  regime (e.g., calm vs volatile periods).
- Cross-sectional IC is preliminary; robust signal validation requires longer historical
  daily snapshots and rolling IC analysis.
