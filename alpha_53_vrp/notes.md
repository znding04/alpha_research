# VRP (Variance Risk Premium) — Alpha 53 Notes

## Hypothesis

**The cross-sectional rank of Variance Risk Premium (VRP = IV² − RV²) across the 6 focus tickers predicts forward equity returns.**

- `VRP > 0` → options expensive (implied volatility > realized volatility) → volatility risk premium (fear premium)
- `VRP < 0` → options cheap (implied < realized) → vol underpriced / complacency
- Cross-sectionally: tickers with the **highest VRP** (most expensive vol) may underperform in forward returns as the premium decays; tickers with the **lowest VRP** may outperform as vol reverts upward.

## Signal Definition

| Step | Rule |
|------|------|
| **Underlying** | 6 focus tickers: AAPL, MSFT, GOOGL, AMZN, SPY, QQQ |
| **Expiration** | Nearest liquid expiration within **14–60 DTE** (anchored near 30-day tenor) |
| **Liquidity filter** | `volume > 10` OR `openInterest > 100` per leg; `0.01 < IV < 3.0`; `lastPrice > 0` |
| **ATM definition** | Strikes within ±2% of current price; median IV across calls+puts; IV > 5% |
| **Realized vol** | Trailing 252-day annualized close-to-close log returns, min-period floor = 60 days |
| **Signal** | `VRP = ATM_IV² − RV²` (variance units); also `VRP_ratio = VRP / RV²` (dimensionless) |

## Files

- `main.py` — computes VRP for 6 focus tickers, writes `data/vrp53_latest.csv`
- `ic_analysis.py` — single-snapshot IC vs 5-day forward returns, synthetic rolling IC demo
- `notes.md` — hypothesis, rationale, design, results, caveats

## Results — Single Snapshot

*Pending — run `python3 alpha_53_vrp/main.py` to generate first snapshot.*

## Caveats

- Single-snapshot IC is underpowered (1 observation per ticker); meaningful IC requires daily signal snapshots accumulated over ≥30–60 trading days.
- yfinance option chains after hours or on non-trading days can return placeholder IVs (e.g., 0.0625, 0.125); the DTE filter (14–60) and IV > 5% guard against most.
- Realized volatility proxy uses close-to-close returns; overnight gaps are not captured. Range-based RV (Parkinson, Garman-Klass) could be a robustness check in future versions.
- The 6-ticker focus is a subset of the full 16-ticker universe used by other VRP alphas (alpha_04, alpha_23, alpha_41, alpha_44, alpha_47); comparison across universes should note the different instrument coverage.

## Signal History

First implementation (2026-11-26): VRP = IV² − RV² for 6 focus tickers, ATM IV from nearest liquid 14–60 DTE expiration, 252-day realized vol with 60-day min-period floor. Future: accumulate daily snapshots, compute rolling IC, and test tradability via validation pipeline.

## Design Rationale

**Why this variant?**
- `alpha_41_vrp_core` uses full 16-ticker universe and DTE range 14–90 (broader)
- `alpha_47_vrp` uses 6 focus tickers and DTE 14–60 with volume-weighted IV across ±5% moneyness
- `alpha_44_vrp_range` uses Parkinson range-based RV (60-day OHLC window)
- `alpha_52_vrp` uses 14–45 DTE narrow window
- **This alpha (53)** uses: **fixed 14–60 DTE window** (broader than alpha_52's 14–45, same as alpha_47 but with strict ±2% moneyness ATM definition), **close-to-close RV with 60-day min floor**. The 14–60 DTE window captures more liquid expirations around the standard 30-day tenor, improving stability of the ATM IV estimate while still anchoring near 30 days.