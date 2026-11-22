# VRP Focus (alpha_49_vrp_focus) — Variance Risk Premium

## Hypothesis

**The variance risk premium (IV^2 - RV^2), computed cross-sectionally across
the 6 focus tickers (AAPL, MSFT, GOOGL, AMZN, SPY, QQQ), captures the
relative pricing of options vs. historical realized volatility.**

- `vrp_variance > 0` → Options relatively expensive (IV^2 > RV^2),
  fear premium earned; call writing / short vol bias
- `vrp_variance < 0` → Historical vol rich relative to implied; long vol bias

Cross-sectionally, tickers with the most positive VRP may exhibit
different forward return characteristics, as the option market prices
tail risk that the historical proxy does not fully capture.

## Signal Definition

| Step | Rule |
|------|------|
| **Underlying** | 6 focus tickers: AAPL, MSFT, GOOGL, AMZN, SPY, QQQ |
| **Expiration** | Nearest liquid expiration within 14–60 DTE |
| **Liquidity filter** | `volume > 10` OR `openInterest > 100` per leg; `0.01 < IV < 3.0`; `lastPrice > 0` |
| **ATM definition** | Strikes within ±3% of current price; volume-weighted IV across calls+puts |
| **Realized vol** | 30-day trailing close-to-close log returns, annualized with √252 |
| **Signal** | `vrp_variance = IV^2 - RV^2` per ticker |

## Files

- `main.py` — computes the VRP signal, writes `data/vrp_focus_latest.csv`
- `ic_analysis.py` — single-snapshot IC vs 5-day forward returns, plus synthetic rolling-IC demo

## Results — Single Snapshot (2026-11-22)

Computed VRP for all 6 focus tickers. Output saved to `data/vrp_focus_latest.csv`.

## Caveats

- Single-snapshot IC is underpowered (1 observation); meaningful IC requires
  daily signal snapshots accumulated over ≥30–60 trading days.
- yfinance option chains after hours or on non-trading days can return
  placeholder IVs; the DTE filter (14–60) and IV > 0.01 guard against most.
- Realized volatility proxy uses close-to-close returns; overnight gaps
  are not captured. Range-based RV (Parkinson, Garman-Klass) could be a
  robustness check in future versions.
- The 6-ticker focus is a subset of the full 16-ticker universe used by
  other VRP alphas (alpha_04, alpha_23, alpha_47); comparison across
  universes should note the different instrument coverage.

## Signal History

First implementation (2026-11-22): VRP = IV^2 - RV^2 for 6 focus tickers,
ATM IV from nearest liquid 14–60 DTE expiration, 30-day realized vol from
close-to-close returns. Future: accumulate daily snapshots, compute rolling
IC, and test tradability via validation pipeline.