# Alpha Research

This repo is dedicated exclusively to **alpha signal discovery** — not strategy backtesting.

## Scope

### What goes here ✅
- Predictive features/signal computation (raw alphas)
- Cross-sectional factor research
- Volatility surface / options IV signals
- Factor decomposition analysis
- Signal decay & predictability tests (IC, IR, turnover)
- Data pipelines for alternative data or raw inputs

### What does NOT go here ❌
- Strategy backtests (→ `QuantConnectProjects/`)
- Trading execution rules (entries/exits, stops)
- Portfolio allocation logic
- Performance attribution at portfolio level

## Folder Structure
```
alpha_research/
├── alpha_*/              # One folder per signal
│   ├── main.py           # Live signal from today's yfinance option chains
│   ├── historical.py     # Historical version from CBOE vol indices (where possible)
│   ├── ic_analysis.py    # Forward-return IC on accumulated live snapshots
│   └── notes.md          # Hypothesis, rationale, results
├── common/
│   ├── universe.py       # Ticker universe (12 ETFs + 4 single names) & CBOE index map
│   ├── history.py        # CBOE implied-vol index + price history loader (cached)
│   ├── ic_engine.py      # Shared historical IC engine (cross-sectional & time-series)
│   ├── hedged.py         # Delta-hedged straddle / variance-swap P&L targets
│   └── utils.py          # IC helpers, forward returns for live snapshots
├── run_historical.py     # Runs every alpha_*/historical.py → results/ + figures/historical/
├── collect_snapshots.py  # Runs every main.py, archives outputs to data/snapshots/<date>/
├── results/              # historical_ic.csv, HISTORICAL.md
├── figures/historical/   # Cumulative IC charts per alpha
├── data/                 # Latest outputs (gitignored); data/snapshots/ IS versioned
└── README.md
```

## Universe

**Live (option chains):** SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO + AAPL, MSFT, GOOGL, AMZN (`common/universe.py`).

**Historical:** the 17 underlyings with a CBOE 30-day implied-vol index: SPY (VIX), QQQ (VXN), IWM (RVX), DIA (VXD), GLD (GVZ), SLV, TLT, EEM, EWZ, FXI, GDX, USO (OVX), AAPL, AMZN, GOOGL, GS, IBM. Most series start 2009–2011, VIX/TLT 2004. No CBOE index exists for MSFT. SPX-only signals use VIX9D/VIX/VIX3M/VIX6M, SKEW and COR3M.

## Implemented Signals

Status legend (2026-10-18). **Live status**: ✅ signal computes on today's chains · 🔄 needs accumulated snapshots · ⚠️ data issue. **Historical IC**: rank IC of the signal vs the next 21-day return (signal at close t, return from close t+1), Newey-West t-stat. **Delta-hedged IC**: IC vs the return of a daily delta-hedged 30d ATM straddle (vol P&L with price exposure removed; `common/hedged.py`). ✅ = |t| ≥ 2, sign as hypothesized and stable post-2019 · ⚠️ = borderline or wrong sign · ❌ = not significant · n/a = smile/OI signals that need option-chain history (no free historical source). Full grid in [results/HISTORICAL.md](results/HISTORICAL.md).

| Signal | Folder | Description | Live status | Historical IC (21d fwd return) | Delta-hedged IC |
|---|---|---|---|---|---|
| **IV Rank** | `alpha_01_iv_rank/` | ATM IV vs median IV spread across liquid contracts | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a |
| **IV Skew Dynamics** | `alpha_02_iv_skew_dynamics/` | 25-delta put-call skew (Black-Scholes delta) at ~30d / ~75d & skew term slope | ✅ Snapshot OK | ❌ **−0.020** (t −0.3), SPY time-series | not yet tested |
| **IV Term Structure Slope** | `alpha_03_iv_term_structure/` | ATM IV term structure slope & far/near ratio (also covers calendar spread) | ✅ Snapshot OK | ✅ **−0.195** (t −2.8), SPY time-series | ⚠️ straddle 1d **+0.131** (t +8.2), 21d to expiry **−0.137** (t −1.9); net of VIX level: return IC −0.08 (t −1.1). Details in notes |
| **VRP (Variance Risk Premium)** | `alpha_04_vrp/` | IV² − RV² variance risk premium | ✅ Snapshot OK | ❌ **+0.007** (t +0.4), 17-name cross-section | not yet tested |
| **IV Rank Percentile** | `alpha_05_iv_rank_percentile/` | Current ATM IV percentile vs 1-year range | ⚠️ Live history synthetic (historical version OK) | ❌ **−0.010** (t −0.6), 17-name cross-section | not yet tested |
| **VRP Term Structure** | `alpha_06_vrp_term_structure/` | VRP slope & curvature across expirations (also covers VRP carry) | ✅ Snapshot OK | ❌ **−0.041** (t −0.6), SPY time-series | not yet tested |
| **IV Dispersion** | `alpha_07_iv_dispersion/` | Index vs constituent IV spread (SPY/QQQ vs top holdings) | ✅ Snapshot OK (SPY, QQQ only) | ⚠️ **+0.119** (t +1.9), SPY time-series | not yet tested |
| **Gamma Exposure (GEX)** | `alpha_08_gamma_exposure/` | Net dealer gamma exposure from OI; zero-gamma flip level | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a |
| **IV Surface Curvature** | `alpha_09_iv_surface_curvature/` | Quadratic OTM smile fit & 25Δ butterfly at ~30 DTE | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a |
| **Vol-of-Vol** | `alpha_11_vol_of_vol/` | Realized vol of ATM IV (20d rolling) | 🔄 Live needs 20d snapshots (historical version OK) | ❌ **+0.028** (t +1.7), 17-name cross-section | not yet tested |
| **IV Momentum** | `alpha_12_iv_momentum/` | 5-day ATM IV change (also covers removed alpha_22) | ⚠️ Live history placeholder (historical version OK) | ❌ **−0.007** (t −0.9), 17-name cross-section | not yet tested |
| **IV Skew Momentum** | `alpha_13_iv_skew_momentum/` | 5-day change of 25-delta put-call skew | 🔄 Live needs snapshots | ❌ **+0.008** (t +0.1), SPY time-series | not yet tested |
| **Put/Call OI-Weighted IV Spread** | `alpha_14_iv_smile_asymmetry/` | Volume/OI-weighted put-call IV spread & put/call ratios | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a |
| **IV Term Structure Momentum** | `alpha_15_iv_term_momentum/` | Rate of change of IV term structure slope | 🔄 Live needs snapshots | ❌ **−0.007** (t −0.1), SPY time-series | not yet tested |
| **IV Skew Convexity** | `alpha_16_iv_skew_convexity/` | Tail butterfly convexity (10Δ/5Δ wings) at ~30 DTE | ✅ Snapshot OK (no DIA) | n/a — needs option-chain snapshots | n/a |
| **IV Surface Skewness** | `alpha_19_iv_surface_skewness/` | 3rd/4th moments of IV smile across strikes | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a |
| **VRP Skew** | `alpha_20_vrp_skew/` | Put VRP minus Call VRP (IV²−RV² asymmetry) | ⚠️ IC script uses synthetic back-filled history | n/a — needs option-chain snapshots | n/a |

**Removed duplicates (2026-10-18):** `alpha_10_vrp_carry` (= VRP term slope, alpha_06), `alpha_17_iv_calendar_spread` (= IV term slope, alpha_03), `alpha_18_vrp_momentum` (its "momentum" is near − mid VRP at one date, = VRP term slope, alpha_06), `alpha_21_iv_percentile` (copy of alpha_05), `alpha_22_iv_change` (5-day ATM IV change, = alpha_12). Numbers are not reused.

## Historical Analysis

Run `python3 run_historical.py` (add `--refresh` to re-download data). Each alpha with a `historical.py` is rebuilt daily from CBOE implied-vol indices, then scored against forward returns (does it predict price?) and forward changes in the underlying's 30d IV (does it predict vol?).

| Alpha | Kind | Hyp. | IC (21d ret) | t | IC post-2019 | IC (21d ΔIV) | t | Verdict |
|---|---|---|---|---|---|---|---|---|
| alpha_02_iv_skew_dynamics | ts | + | -0.020 | -0.3 | -0.121 | +0.124 | +2.0 | ❌ not significant |
| alpha_03_iv_term_structure | ts | − | -0.195 | -2.8 | -0.255 | +0.431 | +6.1 | ✅ significant, as hypothesized |
| alpha_04_vrp | cs | + | +0.007 | +0.4 | +0.035 | -0.144 | -9.5 | ❌ not significant |
| alpha_05_iv_rank_percentile | cs | + | -0.010 | -0.6 | -0.002 | -0.353 | -24.8 | ❌ not significant |
| alpha_06_vrp_term_structure | ts | − | -0.041 | -0.6 | -0.072 | +0.018 | +0.3 | ❌ not significant |
| alpha_07_iv_dispersion | ts | + | +0.120 | +1.9 | +0.213 | -0.252 | -4.0 | ❌ not significant |
| alpha_11_vol_of_vol | cs | − | +0.028 | +1.7 | -0.005 | +0.003 | +0.2 | ❌ not significant |
| alpha_12_iv_momentum | cs | − | -0.007 | -0.9 | -0.008 | -0.142 | -16.3 | ❌ not significant |
| alpha_13_iv_skew_momentum | ts | − | +0.008 | +0.1 | +0.015 | +0.018 | +0.3 | ❌ not significant |
| alpha_15_iv_term_momentum | ts | + | -0.007 | -0.1 | +0.002 | +0.132 | +1.9 | ❌ not significant |

**Key findings**
- **Only the IV term structure (alpha_03) predicts index returns significantly**: backwardation (VIX3M/VIX low) precedes higher returns, IC −0.19 at 21d (t −2.8) for SPY, with the same sign on QQQ/IWM/DIA and post-2019. **But most of it is the VIX level**: VIX alone has IC +0.16 (t +2.7), and the term ratio net of VIX drops to −0.08 (t −1.1).
- **After delta hedging, alpha_03 is a vol-timing signal.** Contango predicts gains on long hedged straddles over 1–5 days (IC +0.13, t ≈ 8 at 1d on all four index ETFs; +0.08, t +5.3 net of VIX), as VIX drifts up toward VIX3M. Held to expiry the sign flips: steep contango favors short vol (hedged straddle −25% in the top quintile vs −16% in backwardation; IC −0.17, t −2.4 net of VIX). Marks use index-derived IVs, not traded option prices, and ignore bid/ask; real-price tests are the next step. See `alpha_03_iv_term_structure/notes.md`.
- **Implied correlation (alpha_07, COR3M)** is borderline: +0.12 at 21d (t +1.9), +0.07 at 5d with t ≈ 2 across all four index ETFs.
- **VRP, IV percentile, IV momentum, vol-of-vol show no return predictability**, cross-sectionally or per ticker. VRP's cross-sectional IC was negative 2011–2017 and positive since 2021, so it is regime-dependent, not a stable premium.
- **Many signals strongly predict the *change in IV*** (IV percentile −0.35, t −25; IV momentum −0.14; VRP −0.14): high or rising IV falls back. That is ordinary vol mean reversion. It is **not directly tradable**: VIX futures and variance swaps already price the expected reversion (the futures curve slopes toward the mean), so a spot-IV forecast is not a P&L forecast. Testing against VIX-futures or straddle returns is the next step before treating these as vol alphas.

**Caveats:** SPX-only signals are a single time series (~15 years, few independent 21-day periods); persistent signals make their t-stats optimistic. CBOE index IVs are 30-day constant-maturity proxies, not the exact ATM IV the live `main.py` scripts compute. Smile-shape and OI-based alphas (01, 08, 09, 14, 16, 19, 20) have no free historical source; they are scored only as live snapshots accumulate (`collect_snapshots.py`).

## Alpha Development Workflow

1. **Hypothesis**: Write `notes.md` with the idea, why it should work, expected decay
2. **Compute**: Generate signal values on a universe of securities over time
3. **Rank**: Cross-sectionally rank instruments by signal strength
4. **Test**: Compute IC, IR, half-life of predictive power
5. **Document**: Record pass/fail, edge cases, look-ahead risks

## Key Files
- `common/ic_engine.py` — the single IC methodology used for all historical results
- `common/history.py` — historical data (CBOE + yfinance), cached in `data/history/`
- `common/utils.py` — IC helpers and forward returns for live snapshots

## Notes
- All alphas must be tested against look-ahead bias
- Use forward-looking returns only (no peeking into future bars)
- Prefer daily resolution unless intraday alpha requires otherwise