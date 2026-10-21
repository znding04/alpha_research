# IV Dispersion (Index vs Constituent) — Alpha Signal Notes

## Hypothesis

**Index options are systematically mispriced relative to their constituents.**

- Index IV (SPY/QQQ) reflects aggregate hedging demand (institutional portfolio insurance)
- Constituent IVs (AAPL, MSFT, GOOGL, AMZN) reflect single-stock supply/demand
- When index IV > weighted constituent IV → index options expensive (fear premium)
- When index IV < weighted constituent IV → index options cheap (complacency)

**Signal**: `Dispersion = Index_ATM_IV - Weighted_Constituent_ATM_IV`

## Why It Should Work

1. **Structural hedging demand**: Institutions buy index puts for portfolio protection, creating persistent bid in index options
2. **Dealer gamma hedging**: Market makers delta-hedge index options, creating mean-reversion pressure
3. **Correlation risk premium**: Index IV embeds correlation risk; constituents don't. When correlation spikes, index IV spikes more
4. **Mean reversion**: Dispersion oscillates around structural equilibrium (typically slightly positive due to hedging demand)

## Expected Decay

- **Horizon**: 5-20 days (index vol mean-reverts faster than single-stock)
- **IC Target**: |IC| > 0.05 for 5-day forward returns
- **Turnover**: Low — dispersion changes slowly (driven by IV levels, not prices)

## Implementation Details

### Weights
Uses approximate top-4 holdings weights:
- **SPY**: AAPL 7%, MSFT 6%, GOOGL 3.5%, AMZN 3.5% (sum = 20% of SPY)
- **QQQ**: AAPL 12%, MSFT 10%, GOOGL 6%, AMZN 5% (sum = 33% of QQQ)

Weights normalized to available constituents each run.

### Data Requirements
- ATM IV for 14-60 DTE expiration (same as alpha_04, alpha_05)
- Daily snapshots to build history for IC analysis
- ~$0.10-0.30 per run (6 tickers × 2 option chains)

### Outputs
- `data/iv_dispersion_latest.csv` — current snapshot
- `data/iv_dispersion_history.json` — persistent history for IC analysis

## Risk Factors / Look-Ahead Checks

✅ **No look-ahead**: Uses only current option chains (available at market close)
✅ **Forward returns**: IC analysis uses 5-day forward returns only
⚠️ **Weights drift**: SPY/QQQ weights change quarterly; should update periodically
⚠️ **Constituent coverage**: Only top 4 names — misses 80%/67% of index weight
⚠️ **Liquidity bias**: Only uses liquid strikes; may miss OTM skew information

## Integration with Other Signals

| Signal | Relationship |
|--------|--------------|
| **alpha_04 VRP** | Dispersion + VRP = index fear vs single-stock fear |
| **alpha_02 Skew** | High put skew + high dispersion = strong hedging demand |
| **alpha_03 Term Structure** | Backwardation + dispersion = near-term panic |
| **alpha_05 IV Percentile** | High percentile + high dispersion = extreme signal |

## Trading Logic (Conceptual)

```
if dispersion > 2% (200 bps):
    → Sell index straddle / Buy constituent straddles (dispersion trade)
elif dispersion < -2%:
    → Buy index straddle / Sell constituent straddles
else:
    → Neutral
```

## Results — expanded ETF universe (2026-10-16 close)

Universe: 12 ETFs (SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO) + AAPL, MSFT, GOOGL, AMZN, from `common/universe.py`. Raw: `data/snapshots/2026-10-16/`.

| index | index_atm_iv | weighted_const_iv | dispersion | dispersion_ratio | n_constituents |
|---|---|---|---|---|---|
| SPY | 0.1547 | 0.3823 | -0.2277 | 0.4046 | 4 |
| QQQ | 0.2411 | 0.3796 | -0.1386 | 0.6350 | 4 |

**ETF vs single-name observations:**
- Dispersion is only defined for SPY and QQQ (top-4 holdings: AAPL, MSFT, GOOGL, AMZN). Other ETFs have no small liquid constituent set, so the universe expansion does not apply here.
- Constituent IV (0.38) is far above index IV (SPY 0.15, QQQ 0.24): implied correlation is low, but the constituent IVs are inflated by late-Oct earnings, so the ratio overstates dispersion today.

## IC Analysis

Run `ic_analysis.py` after building 20+ days of history:
- Computes Spearman rank IC between dispersion and 5-day forward index returns
- Tracks IR, win rate, max/min IC
- Requires `data/iv_dispersion_history.json` populated by daily `main.py` runs

## Next Steps

1. [ ] Run daily for 30+ days to build history
2. [ ] Compute IC and validate predictive power
3. [ ] Add rolling weights from actual SPY/QQQ holdings (via ETF fact sheets)
4. [ ] Test dispersion + VRP combo signal
5. [ ] Add constituent correlation regime detection

## Historical Analysis (CBOE implied-vol indices, through 2026-10-16)

Signal: **SPX implied correlation (COR3M)** (`historical.py`). Hypothesized IC sign vs forward returns: **+**. Signal at close t, forward window from close t+1. `cs` = daily cross-sectional rank IC (NW t-stat); `ts` = per-ticker time-series rank IC, averaged (t ≈ IC·√(N/h)). Run: `python3 run_historical.py alpha_07`.

| Target | Kind | 1d IC (t) | 5d IC (t) | 21d IC (t) | 21d IC post-2019 |
|---|---|---|---|---|---|
| Fwd return | ts | +0.026 (+1.9) | +0.066 (+2.1) | +0.119 (+1.9) | +0.213 |
| Fwd Δlog IV | ts | -0.069 (-5.0) | -0.133 (-4.3) | -0.252 (-4.0) | -0.295 |

**Interpretation:** Borderline. High implied correlation (COR3M) precedes higher index returns: +0.07 at 5d (t ≈ 2 for SPY/QQQ/IWM/DIA), +0.12 at 21d (t +1.9), +0.21 post-2019. Also predicts VIX falling (−0.25, t −4.0). Worth keeping; needs out-of-sample confirmation.

![cumulative IC](../figures/historical/alpha_07_iv_dispersion.png)

## Tradability Validation (pre-registered 2026-10-20) — VERDICT: NOT a valid alpha (promising lead on VIX futures)

Design in `validation.py` (written before any strategy numbers were computed), shared rule in `common/validation.py`, run with `python3 run_validation.py alpha_07`. Signal: COR3M at close t, unchanged. In-sample 2009–2018 picks only the direction; out-of-sample 2019–2026 judges, after costs, 1-day lag. Strategy w = s·(2·trailing-252d percentile − 1).

| Test (OOS 2019–2026) | IC vs 5d fwd return | Alpha vs all benchmarks | Net return (Sharpe) | Result |
|---|---|---|---|---|
| **Primary: time SPY** (controls: buy & hold, VIX-level timing) | +0.112 (t +2.2), IS +0.107 | +2.0%/yr (t +0.9) | +2.3%/yr (0.22) vs buy & hold +17.1%/yr (0.92) | **FAIL** (ii) |
| Secondary: time 30d VIX futures (controls: always short, VIX level, futures basis) | −0.157 (t −3.1), IS −0.145 | **+26.0%/yr (t +1.9)**; full sample t +2.9 | +4.0%/yr (0.34) vs always short +12.3%/yr (0.56) | fail (not scored) |

**Reading:**
1. **On SPY it is VIX-level timing.** The return IC is real and stable (IS and OOS both ≈ +0.11), but the timing strategy has beta 0.94 to "buy when VIX is high" and no residual alpha. A long/short timing rule also gives up the equity premium: +2%/yr vs +17%/yr buy & hold.
2. **On VIX futures it is the strongest result in the repo.** High implied correlation predicts VIX futures falling (IC −0.16 OOS, same sign and size as IS), and the timing strategy beats the VIX-level and futures-basis strategies by +26%/yr (t +1.9 OOS, +2.9 over the full sample). Unlike alpha_03, it is **not** the futures basis in disguise (beta −0.09 to basis timing). It misses the t ≥ 2 bar narrowly, the strategy still has a −80% drawdown, and this was a secondary test, so it cannot be promoted after the fact.
3. **Next step (new pre-registration, forward data only):** make "COR3M → short VIX futures" a primary test judged only on data after 2026-10-20 (paper-trade), or on an independent instrument (e.g. VSTOXX futures with the Euro Stoxx implied-correlation analogue). Re-scoring the same 2019–2026 window would be data snooping.
