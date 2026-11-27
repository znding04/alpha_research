# IV Skew Dynamics — Alpha 54 Notes

## Hypothesis

**The cross-sectional rank of IV put-call skew across the 6 focus tickers, and its 5-day change (Δskew), predicts forward equity returns.**

- `skew = IV(put ≈ 95% spot) − IV(call ≈ 105% spot)` at ~30 DTE
- `skew > 0` → put IV richer than call IV → downside tail fear (skew bid)
- `skew < 0` → call IV richer than put IV → upside call demand / complacency
- Cross-sectionally: tickers with the **highest skew** (most put-bid) may outperform or underperform depending on whether skew signals fear (mean-reversion long) or is a priced risk premium (fear premium = underperformance)
- **Δskew** (5-day change in skew): rising skew → fear building; falling skew → fear dissipating

## Signal Definition

| Step | Rule |
|------|------|
| **Underlying** | 6 focus tickers: AAPL, MSFT, GOOGL, AMZN, SPY, QQQ |
| **Expiration** | Nearest liquid expiration within ~30 DTE ± 8 days |
| **Liquidity filter** | `volume > 5` OR `openInterest > 50` per leg; `0.05 < IV < 3.0`; `lastPrice > 0` |
| **Put leg** | Nearest OTM put strike ≈ 95% of spot (±3% tolerance band, fallback to nearest OTM put) |
| **Call leg** | Nearest OTM call strike ≈ 105% of spot (±3% tolerance band, fallback to nearest OTM call) |
| **Signal** | `skew = put_IV − call_IV` (vol units, also reported in basis points ×10000) |
| **Dynamics** | Δ5d skew = skew(today) − skew(5 trading days ago) from persisted history |

## Files

- `main.py` — computes skew for 6 focus tickers, writes `data/iv_skew_54_latest.csv`, persists history to `data/iv_skew_54_history.json`
- `ic_analysis.py` — single-snapshot IC vs 5-day forward returns on skew level and skew change; synthetic rolling IC demo
- `notes.md` — hypothesis, rationale, design, results, caveats

## Results — Single Snapshot (2026-11-27)

*First snapshot generated on 2026-11-27. All IVs returned 0.0625 (yfinance floor on non-trading day / after-hours), yielding skew = 0.0 for all tickers. Forward returns not yet available. IC = N/A. This snapshot is degenerate due to data source issue; meaningful analysis requires a normal trading day.*

## Caveats

- **yfinance IV data quality**: On non-trading days, after hours, or during data delays, yfinance returns placeholder IVs (commonly 0.0625 = 1/16 = 6.25%, or 0.125, 0.25). These are not market IVs. The `IV > 0.05` filter cannot distinguish these floors from real low IVs. **On a normal trading day, IVs should range 10–50%+.**
- Single-snapshot IC is underpowered (1 observation per ticker); meaningful IC requires daily signal snapshots accumulated over ≥30–60 trading days.
- Fixed-moneyness skew (95%/105%) is an approximation of true 25-delta risk reversal; it avoids Black-Scholes delta root-finding but has a different scaling.
- Realized volatility is not used in this signal (unlike VRP alphas); this is a pure options-skew metric.
- The 6-ticker focus matches alpha_47/52/53 VRP variants for direct cross-comparison.

## Signal History

First implementation (2026-11-27): IV Skew Dynamics — put-call skew at fixed moneyness (95% put, 105% call) at ~30 DTE, cross-sectional rank over 6 focus tickers, 5-day skew change from persisted history. Output → `data/iv_skew_54_latest.csv`. History → `data/iv_skew_54_history.json`. Future: accumulate daily snapshots, compute rolling IC, and test tradability via validation pipeline.

## Design Rationale

**Why fixed moneyness (not delta-solved)?**
- Delta-solved risk reversal (25Δ RR) requires Black-Scholes root-finding against chain-interpolated IV. The delta column in yfinance is often missing or stale. The BS solve adds complexity and failure modes (no convergence, bad IV surface).
- Fixed moneyness (95%/105%) is transparent, deterministic, and requires only the `impliedVolatility` field from yfinance — the same field all live alphas rely on.
- 95%/105% corresponds roughly to 25-delta for typical SPY/ETF smiles but is invariant to IV level and smile shape changes.
- Prior delta-solved alphas (02, 42, 51) exist; this variant provides a robust, dependency-free alternative for live snapshot generation.

**Why skew *change* (Δskew) not just level?**
- Skew level is persistent (structural: puts are chronically richer than calls). The *change* in skew captures shifting sentiment: fear building vs. fear dissipating.
- Persisting daily snapshots enables Δskew computation once ≥2 snapshots exist; forward-return IC on Δskew is the primary edge test.

**Why 6 focus tickers?**
- Matches the cross-sectional design of alpha_47/52/53 (VRP variants) for apples-to-apples IC comparison.
- Single names (AAPL, MSFT, GOOGL, AMZN) have more pronounced skew; ETFs (SPY, QQQ) have flatter smiles. The cross-section captures this dispersion.