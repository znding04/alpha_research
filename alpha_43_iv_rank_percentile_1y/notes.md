# IV Rank Percentile (1-Year Snapshot History) — Alpha Signal Notes

## Hypothesis

**The percentile rank of current ATM implied volatility (IV) relative to 1 year of accumulated daily option-chain snapshots predicts forward returns via mean reversion of volatility regimes.**

- `iv_percentile_1y > 0.8` → ATM IV is in the top 20% of its 1-year historical range → IV is relatively expensive → volatility mean reversion likely → **bearish for equity / short volatility opportunity**
- `iv_percentile_1y < 0.2` → ATM IV is in the bottom 20% of its 1-year range → IV is cheap → potential for volatility expansion → **bullish for equity / long volatility opportunity**
- `0.2 ≤ iv_percentile_1y ≤ 0.8` → Normal regime, no strong signal

**Mechanism:** Volatility is mean-reverting. When IV rises to the extremes of its recent distribution, it signals an overbought/oversold volatility state. The cross-sectional percentile rank isolates relative mispricing across tickers driven by the same macro factor.

## Signal Definition

| Step | Rule |
|------|------|
| **Expiration** | Nearest liquid expiration (skip DTE < 2, max 180 DTE) |
| **Liquidity filter** | `volume > 10` OR `openInterest > 100`; `0.01 < IV < 3.0`; `lastPrice > 0`; ≥ 10 contracts |
| **ATM IV** | Median IV of strikes within ±2% moneyness (IV > 5%); fallback = closest strike with IV > 5% |
| **Historical range** | Empirical min/max ATM IV from accumulated daily snapshots in `data/snapshots/` over past 365 days |
| **Percentile** | `(atm_iv - min_iv) / (max_iv - min_iv)`, clipped to [0, 1] |
| **Minimum history** | ≥ 20 days of snapshots required; otherwise defaults to 0.5 |

## Data Sources

- **Live ATM IV:** yfinance option chains (current day)
- **Historical ATM IVs:** `data/snapshots/<YYYY-MM-DD>/iv_rank_latest.csv` files created daily by `collect_snapshots.py` (runs `alpha_01_iv_rank/main.py` and archives output)
- **Universe:** 16 tickers from `common/universe.py` (12 ETFs + 4 single names: SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO, AAPL, MSFT, GOOGL, AMZN)

## Files

- `main.py` — Computes live ATM IV + 1-year percentile; writes `data/iv_rank_percentile_1y_latest.csv`
- `ic_analysis.py` — Computes IC vs 5-day forward returns; simulates rolling IC for demonstration
- `notes.md` — This document

## Output Format

`data/iv_rank_percentile_1y_latest.csv`:
```csv
ticker,date,current_price,atm_iv,iv_percentile_1y,n_contracts,percentile_date
SPY,2026-11-16,754.37,0.1829,0.8432,206,2026-11-15
QQQ,2026-11-16,679.89,0.2532,0.7123,229,2026-11-15
...
```

- `date`: Signal snapshot date (today)
- `percentile_date`: Most recent historical snapshot date used for percentile calculation

## Relationship to Existing Signals

| Signal | Folder | Key Difference |
|--------|--------|----------------|
| IV Rank | `alpha_01_iv_rank/` | ATM IV vs median IV spread (no percentile) |
| IV Rank Percentile (CBOE) | `alpha_05_iv_rank_percentile/` | Uses CBOE implied vol indices for 1y history (historical only) |
| IV Rank Percentile (30d) | `alpha_30_iv_rank_percentile/` | ATM IV vs near-term option-chain range (30d window) |
| IV Rank Percentile (60d) | `alpha_32_iv_rank_percentile/` | 60d proxy via VIX term structure regime adjustment |
| IV Rank Percentile (Cross-strike) | `alpha_36_iv_rank_percentile/` | Uses cross-strike IV distribution as historical proxy |
| **This signal** | `alpha_43_iv_rank_percentile_1y/` | **True 1-year percentile from accumulated daily option-chain snapshots** |

**Why this is new:** This is the only signal that computes a true 1-year percentile rank using actual daily ATM IVs accumulated from real option-chain snapshots (`data/snapshots/`). All other signals use proxies (CBOE indices, intraday proxies, fixed windows, or cross-strike distributions).

## IC Analysis

- **Real IC:** Not available yet — requires ≥30 daily signal snapshots to accumulate meaningful cross-sectional IC.
- **Method:** `ic_analysis.py` uses `common.utils.compute_ic` (Spearman rank correlation) between `iv_percentile_1y` and 5-day forward returns from `common.utils.forward_return`.
- **Threshold:** `compute_ic` requires ≥10 observations; a single snapshot of 16 tickers produces 16 observations per date — sufficient for cross-sectional IC once multiple dates exist.
- **Rolling IC demo:** The script includes a synthetic rolling IC simulation (using random walk data) to demonstrate the pipeline — **not evidence of predictive power**.

## Expected Behavior

| Market Regime | Expected Signal | Expected Forward Return (High Pctl) | Expected Forward Return (Low Pctl) |
|---------------|-----------------|-------------------------------------|-------------------------------------|
| Calm / Low Vol | Most tickers near 0.5 | Near zero | Near zero |
| Vol Expansion (stress) | Many tickers > 0.8 | Negative (mean reversion) | — |
| Vol Compression | Many tickers < 0.2 | — | Positive (vol expansion) |
| Cross-sectional dispersion | Wide spread across tickers | High percentile tickers underperform | Low percentile tickers outperform |

**Rationale for sign:** High IV percentile → IV expensive → sellers of volatility (short straddles, variance swaps) earn premium → forward equity returns tend to be lower as market prices in vol risk. Low IV percentile → IV cheap → potential for vol expansion → forward equity returns may benefit from vol mean reversion.

## Caveats & Limitations

1. **No free historical option-chain source:** The signal depends entirely on accumulated snapshots from `collect_snapshots.py`. First ~30 days of operation will have default 0.5 percentiles.
2. **Snapshot quality varies:** yfinance may return placeholder IVs (e.g., 0.0625) on some days; these outliers can distort the historical range. Future version could add outlier filtering.
3. **Ticker additions:** New tickers added to universe will have no history initially; their percentile defaults to 0.5.
4. **IV data quality:** yfinance IVs are mid-price implied vols; bid/ask spreads and model assumptions (Black-Scholes) introduce noise.
5. **Survivorship bias:** The snapshot archive only includes tickers that were in the universe at snapshot time.
6. **Percentile stability:** With only ~20-60 days of history initially, percentiles can be noisy. Signal becomes more reliable after 60+ trading days.

## Example Snapshot (2026-11-16 — First Run, No History)

```
🔍 IV Rank Percentile (1Y History) — 2026-11-16 02:11
======================================================================
Loading historical ATM IVs from data/snapshots/...
  ⚠️ No iv_rank_latest.csv files found in snapshots
  No historical data found - percentiles will default to 0.5
  SPY: ATM IV=0.0625, 1Y Pctl=0.5000 (n=121)
  QQQ: ATM IV=0.0625, 1Y Pctl=0.5000 (n=134)
  ...
```

All percentiles default to 0.5 because `data/snapshots/` contains no `iv_rank_latest.csv` files yet. As `collect_snapshots.py` runs daily, the archive will build up and percentiles will become meaningful.

## Future Enhancements

1. **Outlier filtering:** Remove IV spikes > 3× median from historical range before computing percentile.
2. **Weighted percentile:** Use exponentially weighted historical IVs (recent days matter more).
3. **Regime-conditional:** Apply different percentile thresholds based on VIX term structure (contango/backwardation).
4. **Cross-sectional normalization:** Rank percentiles across tickers each day to isolate relative extremes.
5. **Historical IC engine:** Once ≥30 snapshots exist, run `run_historical.py` with a new `historical.py` to compute IC vs 21-day forward returns and 21-day ΔIV.

## Validation Status

| Test | Status |
|------|--------|
| Live snapshot | ✅ Works (produces `data/iv_rank_percentile_1y_latest.csv`) |
| IC analysis | ✅ Runs (returns N/A until forward returns available) |
| Historical IC | ⏳ Needs ≥30 daily snapshots |
| Delta-hedged IC | ⏳ Needs accumulated history |
| Tradability test | ⏳ Requires historical IC first |

## Quick Reference

```bash
# Run live signal
python3 alpha_43_iv_rank_percentile_1y/main.py

# Run IC analysis
python3 alpha_43_iv_rank_percentile_1y/ic_analysis.py

# View latest signal
cat data/iv_rank_percentile_1y_latest.csv

# View historical snapshots
ls data/snapshots/
```