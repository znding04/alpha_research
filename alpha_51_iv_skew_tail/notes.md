# IV Skew Dynamics (alpha_51) — 25Δ Put-Call Risk Reversal (RR25)

## Hypothesis

**Cross-sectional 25-delta put-call risk reversal (RR25) captures relative tail-risk pricing across tickers.**

- RR25 = IV_put(25Δ) − IV_call(25Δ) at ~30 DTE, solved via Black-Scholes delta root-finding
- Positive RR25 → put IV richer than call IV → downside skew (bearish tail fear)
- Negative RR25 → call IV richer than put IV → upside skew (bullish tail fear)
- Cross-sectionally, tickers with extreme positive RR25 may exhibit different forward return characteristics

## Signal Definition

| Step | Rule |
|------|------|
| **Underlying** | 6 focus tickers: AAPL, MSFT, GOOGL, AMZN, SPY, QQQ |
| **Expiration** | Nearest liquid expiration within 20–60 DTE |
| **Liquidity filter** | `volume > 10` OR `openInterest > 100` per leg; `0.01 < IV < 3.0`; `lastPrice > 0` |
| **ATM definition** | Strikes within ±3% of current price; volume-weighted IV across calls+puts |
| **Realized vol** | 30-day trailing close-to-close log returns, annualized with √252 |
| **Signal** | RR25 = IV_put(25Δ) − IV_call(25Δ) per ticker (via BS delta solve) |

## Files

- `main.py` — computes RR25 skew signal, writes `data/iv_skew_latest.csv`
- `ic_analysis.py` — single-snapshot IC vs 5-day forward returns

## Results — Single Snapshot

Computed VRP for all 6 focus tickers. Output saved to `data/iv_skew_latest.csv`.

## Caveats

- Single-snapshot IC is underpowered (1 observation); meaningful IC requires daily signal snapshots accumulated over ≥30–60 trading days.
- yfinance option chains after hours or on non-trading days can return placeholder IVs; the DTE filter (20–60) and IV > 0.01 guard against most.
- Realized volatility proxy uses close-to-close returns; overnight gaps are not captured. Range-based RV (Parkinson, Garman-Klass) could be a robustness check in future versions.
- The 6-ticker focus is a subset of the full 16-ticker universe used by other VRP alphas (alpha_04, alpha_23, alpha_47); comparison across universes should note the different instrument coverage.

## Signal History

First implementation (2026-11-24): VRP = IV^2 - RV^2 for 6 focus tickers, ATM IV from nearest liquid 20–60 DTE expiration, 30-day realized vol from close-to-close returns. Future: accumulate daily snapshots, compute rolling IC, and test tradability via validation pipeline.