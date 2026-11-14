# VRP Core (IV² − RV²) — Alpha Signal Notes

## Hypothesis

**The variance risk premium (VRP) — the gap between implied and realized variance — contains cross-sectional information about forward equity returns.**

### Rationale

1. **Implied > realized = vol risk premium collection.** When the market prices vol higher than what materializes, sellers of vol / variance swaps earn a premium. This tends to compress over time, so high VRP tickers are "expensive vol" — expected future alpha is negative for vol buyers and positive for systematic vol sellers.
2. **Implied < realized = underpriced vol.** When realized moves exceed implied pricing, vol is cheap; this usually coincides with stress / dislocation.
3. **Cross-sectional ranking.** Ranking the core 6 tickers (AAPL, SPY, QQQ, MSFT, GOOGL, AMZN) by VRP isolates the relative mispricing of volatility between instruments that are otherwise driven by the same macro factor.

## Signal Definition

| Step | Rule |
|------|------|
| ATM IV | Median IV of strikes within ±2% moneyness (IV > 5%) from nearest liquid expiration |
| Realized Vol | 252-day trailing annualized realized volatility from daily log returns |
| **VRP (variance)** | `VRP = atm_iv² − rv_252d²` |
| VRP Ratio | `VRP_ratio = VRP / rv_252d²` (normalized) |

### Interpretation

- `VRP > 0` → options expensive (implied > realized)
- `VRP < 0` → options cheap (realized > implied)
- Cross-sectionally: most positive VRP = most expensive vol; most negative VRP = cheapest vol

## Data Source & Limitations

**Source:** yfinance option chains (nearest expiration, up to ~90 DTE) + yfinance daily price history (1y period).

**Limitations:**

1. **yfinance IV quality** — placeholder IVs (e.g. 0.0625) appear frequently, especially for near-term expirations; guards like `IV > 0.01` and `IV > 0.05` for ATM are applied but cannot eliminate all noise.
2. **RV window** — 252-day RV is slow-moving; realized vol can spike quickly, making VRP look negative in crises.
3. **Single snapshot** — IC analysis requires accumulated daily snapshots from `collect_snapshots.py`; a single-day IC is noise.
4. **6 tickers** — enough for a rank IC but below the 10-observation minimum in `compute_ic`; treat single-day IC as descriptive only.

## Files

- `main.py` — computes VRP signal, writes `data/vrp_core_latest.csv`
- `ic_analysis.py` — single-snapshot IC + synthetic rolling-IC demo (not evidence of predictability)

## Next Steps

1. Accumulate daily snapshots via `collect_snapshots.py`
2. Compute rolling IC (≥60 trading days)
3. Test pre-registered tradability on SPX VIX futures or delta-hedged straddles (see `run_validation.py`)
