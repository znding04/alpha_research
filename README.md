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
│   ├── validation.py     # Pre-registered tradability test (design in its docstring)
│   ├── ic_analysis.py    # Forward-return IC on accumulated live snapshots
│   └── notes.md          # Hypothesis, rationale, results
├── common/
│   ├── universe.py       # Ticker universe (12 ETFs + 4 single names) & CBOE index map
│   ├── history.py        # CBOE implied-vol index + price history loader (cached)
│   ├── ic_engine.py      # Shared historical IC engine (cross-sectional & time-series)
│   ├── hedged.py         # Delta-hedged straddle / variance-swap P&L targets
│   ├── vix_futures.py    # CBOE VX settlements → 30d constant-maturity VIX futures returns
│   ├── validation.py     # Shared tradability test: strategies, benchmarks, alpha regression, pass rule
│   ├── instruments.py    # Tradable instruments + cost assumptions (SPY, VIX futures, VIXY, hedged straddles)
│   └── utils.py          # IC helpers, forward returns for live snapshots
├── run_historical.py     # Runs every alpha_*/historical.py → results/ + figures/historical/
├── run_validation.py     # Runs every alpha_*/validation.py → results/VALIDATION.md + figures/validation/ (--selftest)
├── collect_snapshots.py  # Runs every main.py, archives outputs to data/snapshots/<date>/
├── results/              # historical_ic.csv, HISTORICAL.md, VALIDATION.md, validation/
├── figures/              # historical/ (cumulative IC), validation/ (strategy equity curves)
├── data/                 # Latest outputs (gitignored); data/snapshots/ IS versioned
└── README.md
```

## Universe

**Live (option chains):** SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO + AAPL, MSFT, GOOGL, AMZN (`common/universe.py`).

**Historical:** the 17 underlyings with a CBOE 30-day implied-vol index: SPY (VIX), QQQ (VXN), IWM (RVX), DIA (VXD), GLD (GVZ), SLV, TLT, EEM, EWZ, FXI, GDX, USO (OVX), AAPL, AMZN, GOOGL, GS, IBM. Most series start 2009–2011, VIX/TLT 2004. No CBOE index exists for MSFT. SPX-only signals use VIX9D/VIX/VIX3M/VIX6M, SKEW and COR3M.

## Implemented Signals

Status legend (2026-10-20). **Live status**: ✅ signal computes on today's chains · 🔄 needs accumulated snapshots · ⚠️ data issue. **Historical IC**: rank IC of the signal vs the next 21-day return (signal at close t, return from close t+1), Newey-West t-stat. **Delta-hedged IC**: IC vs the return of a daily delta-hedged 30d ATM straddle (vol P&L with price exposure removed; `common/hedged.py`). ✅ = |t| ≥ 2, sign as hypothesized and stable post-2019 · ⚠️ = borderline or wrong sign · ❌ = not significant · n/a = smile/OI signals that need option-chain history (no free historical source). Full grid in [results/HISTORICAL.md](results/HISTORICAL.md). **Tradability test**: pre-registered out-of-sample (2019+) test on a tradable instrument after costs, against benchmark strategies; see [Tradability Validation](#tradability-validation) and [results/VALIDATION.md](results/VALIDATION.md).

| Signal | Folder | Description | Live status | Historical IC (21d fwd return) | Delta-hedged IC | Tradability test |
|---|---|---|---|---|---|---|
| **IV Rank** | `alpha_01_iv_rank/` | ATM IV vs median IV spread across liquid contracts | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a | n/a |
| **IV Skew Dynamics** | `alpha_02_iv_skew_dynamics/` | 25-delta put-call skew (Black-Scholes delta) at ~30d / ~75d & skew term slope | ✅ Snapshot OK | ❌ **−0.020** (t −0.3), SPY time-series | not yet tested | not tested (historical IC not significant) |
| **IV Term Structure Slope** | `alpha_03_iv_term_structure/` | ATM IV term structure slope & far/near ratio (also covers calendar spread) | ✅ Snapshot OK | ❌ **Rejected (VIX-futures test)**. Return IC −0.195 (t −2.8) is mostly the VIX level; no tradable alpha net of the futures basis (OOS alpha +5%/yr, t +1.3) | straddle 1d **+0.131** (t +8.2), 21d to expiry **−0.137** (t −1.9); priced in by VIX futures. Details in notes | ❌ FAIL — VIX futures: OOS IC +0.15 (t +3.0) but alpha +6%/yr (t +1.5) = futures basis |
| **VRP (Variance Risk Premium)** | `alpha_04_vrp/` | IV² − RV² variance risk premium | ✅ Snapshot OK | ❌ **+0.007** (t +0.4), 17-name cross-section | not yet tested | ❌ FAIL — hedged straddles: IC −0.03, gross Sharpe 0.89, break-even cost 0.6% < spreads |
| **IV Rank Percentile** | `alpha_05_iv_rank_percentile/` | Current ATM IV percentile vs 1-year range | ⚠️ Live history synthetic (historical version OK) | ❌ **−0.010** (t −0.6), 17-name cross-section | not yet tested | ❌ FAIL — hedged straddles: OOS IC −0.084 (t −5.0), gross Sharpe 1.35, but break-even cost 0.8% of premium |
| **VRP Term Structure** | `alpha_06_vrp_term_structure/` | VRP slope & curvature across expirations (also covers VRP carry) | ✅ Snapshot OK | ❌ **−0.041** (t −0.6), SPY time-series | not yet tested | not tested (historical IC not significant) |
| **IV Dispersion** | `alpha_07_iv_dispersion/` | Index vs constituent IV spread (SPY/QQQ vs top holdings) | ✅ Snapshot OK (SPY, QQQ only) | ⚠️ **+0.119** (t +1.9), SPY time-series | not yet tested | ❌ FAIL on SPY (= VIX-level timing). Lead: VIX futures alpha +26%/yr (t +1.9, secondary) |
| **Gamma Exposure (GEX)** | `alpha_08_gamma_exposure/` | Net dealer gamma exposure from OI; zero-gamma flip level | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a | n/a |
| **IV Surface Curvature** | `alpha_09_iv_surface_curvature/` | Quadratic OTM smile fit & 25Δ butterfly at ~30 DTE | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a | n/a |
| **Vol-of-Vol** | `alpha_11_vol_of_vol/` | Realized vol of ATM IV (20d rolling) | 🔄 Live needs 20d snapshots (historical version OK) | ❌ **+0.028** (t +1.7), 17-name cross-section | not yet tested | not tested (historical IC not significant) |
| **IV Momentum** | `alpha_12_iv_momentum/` | 5-day ATM IV change (also covers removed alpha_22) | ⚠️ Live history placeholder (historical version OK) | ❌ **−0.007** (t −0.9), 17-name cross-section | not yet tested | ❌ FAIL — hedged straddles: OOS IC −0.064 (t −3.7), gross Sharpe 0.52, break-even 0.4% |
| **IV Skew Momentum** | `alpha_13_iv_skew_momentum/` | 5-day change of 25-delta put-call skew | 🔄 Live needs snapshots | ❌ **+0.008** (t +0.1), SPY time-series | not yet tested | not tested (historical IC not significant) |
| **Put/Call OI-Weighted IV Spread** | `alpha_14_iv_smile_asymmetry/` | Volume/OI-weighted put-call IV spread & put/call ratios | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a | n/a |
| **IV Term Structure Momentum** | `alpha_15_iv_term_momentum/` | Rate of change of IV term structure slope | 🔄 Live needs snapshots | ❌ **−0.007** (t −0.1), SPY time-series | not yet tested | not tested (historical IC not significant) |
| **IV Skew Convexity** | `alpha_16_iv_skew_convexity/` | Tail butterfly convexity (10Δ/5Δ wings) at ~30 DTE | ✅ Snapshot OK (no DIA) | n/a — needs option-chain snapshots | n/a | n/a |
| **IV Surface Skewness** | `alpha_19_iv_surface_skewness/` | 3rd/4th moments of IV smile across strikes | ✅ Snapshot OK | n/a — needs option-chain snapshots | n/a | n/a |
|| **VRP Skew** | `alpha_20_vrp_skew/` | Put VRP minus Call VRP (IV²−RV² asymmetry) | ⚠️ IC script uses synthetic back-filled history | n/a — needs option-chain snapshots | n/a | n/a |
|| **VRP Change** | `alpha_21_vrp/` | Day-over-day change in variance risk premium (IV² − RV²) | ✅ Snapshot OK; 🔄 needs 2+ days history for change | n/a — needs snapshots | n/a | n/a |
||| **Put-Call Parity Residual** | `alpha_22_put_call_parity/` | Put-call parity residual (C−P vs S−Ke^{-(r−q)T}) using traded mid prices; captures borrow-cost / skew anomalies | ✅ Snapshot OK; 4 tickers (after-hours quote limits) | n/a — needs option-chain snapshots | n/a | n/a |
||| **VRP Refined** | `alpha_23_vrp/` | IV² − RV² with 30d RV, cross-section rank (live, 16 tickers); refined over alpha_04 | ✅ Snapshot OK (16 tickers, 2026-10-24) | n/a — needs 30+d daily snapshots for stable IC | not yet tested | not tested |
|| **IV Skew Momentum Refined** | `alpha_24_iv_skew_momentum_refined/` | 5-day change in 25-delta put-call skew using Black-Scholes delta interpolation | ✅ Snapshot OK (13 tickers) | n/a — needs accumulated snapshots | n/a | n/a |

**Removed duplicates

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
- **The best candidate, the IV term structure (alpha_03), failed a pre-registered tradability test.** It predicts index returns (IC −0.19 at 21d, t −2.8) and delta-hedged straddle returns (IC +0.13 at 1d, t +8), but the return IC is mostly the VIX level, and on VIX futures (2019–2026 out-of-sample, after costs) its timing strategy is a near-copy of futures-basis timing (beta 1.00) with no significant extra return (+5%/yr, t +1.3). VIX futures lose money in every signal quintile, so the signal ranks losses rather than finding gains. Verdict: real information about volatility, but already priced; not a valid alpha. Details: `alpha_03_iv_term_structure/notes.md`.
- **Implied correlation (alpha_07, COR3M)** is borderline: +0.12 at 21d (t +1.9), +0.07 at 5d with t ≈ 2 across all four index ETFs.
- **VRP, IV percentile, IV momentum, vol-of-vol show no return predictability**, cross-sectionally or per ticker. VRP's cross-sectional IC was negative 2011–2017 and positive since 2021, so it is regime-dependent, not a stable premium.
- **Many signals strongly predict the *change in IV*** (IV percentile −0.35, t −25; IV momentum −0.14; VRP −0.14): high or rising IV falls back. That is ordinary vol mean reversion. It is **not directly tradable**: VIX futures and variance swaps already price the expected reversion (the futures curve slopes toward the mean), so a spot-IV forecast is not a P&L forecast. Testing against VIX-futures or straddle returns is the next step before treating these as vol alphas.

**Caveats:** SPX-only signals are a single time series (~15 years, few independent 21-day periods); persistent signals make their t-stats optimistic. CBOE index IVs are 30-day constant-maturity proxies, not the exact ATM IV the live `main.py` scripts compute. Smile-shape and OI-based alphas (01, 08, 09, 14, 16, 19, 20) have no free historical source; they are scored only as live snapshots accumulate (`collect_snapshots.py`).

## Tradability Validation

An IC is not an alpha. Run `python3 run_validation.py` (all alphas with a `validation.py`) or `python3 run_validation.py --selftest` (a look-ahead signal must pass and a random one must fail; it does). Every test follows the same rule (`common/validation.py`):

1. **Pre-register.** The design (signal, primary instrument, controls, costs) goes in the alpha's `validation.py` docstring *before* any strategy numbers exist. Only the primary test decides; secondary tests are context and cannot be promoted after the fact.
2. **Tradable instrument + costs** (`common/instruments.py`): SPY (1 bp), 30d constant-maturity VIX futures (0.025 vol-pt half-spread), VIXY (5 bp + 3% borrow), or a weekly long/short book of delta-hedged 30d straddles (3% of premium round trip).
3. **Fit only the direction in-sample** (≤ 2018); judge out-of-sample (2019+), 1-day lag.
4. **Pass** = OOS IC with the in-sample sign and |t| ≥ 2, **and** positive OOS alpha (Newey-West t ≥ 2) after regressing on every benchmark (buy & hold / always short, VIX-level timing, futures-basis timing, equal-weight short straddles, IV-level long/short).
5. Report gross returns and the **break-even cost** too, so a failure says how far the signal is from tradable.

Pre-registered test per alpha (design in each `alpha_*/validation.py`, rule in `common/validation.py`). In-sample ≤ 2018-12-31 (only the trade direction is chosen there), out-of-sample ≥ 2019-01-01, after costs, 1-day execution lag. **Pass** = OOS IC with the in-sample sign and |t| ≥ 2, **and** positive OOS alpha (NW t ≥ 2) after regressing on every benchmark strategy. Only the primary test decides; secondary tests are context.

| Alpha | Signal | Test | Instrument | IS IC | OOS IC (t) | OOS alpha /yr (t) | OOS net ret /yr (Sharpe) | OOS gross Sharpe | Break-even cost (assumed) | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| alpha_03_iv_term_structure | IV term structure (VIX3M/VIX − 1) | primary | 30d VIX futures | +0.062 | +0.149 (+3.0) | +6.1% (+1.5) | -9.7% (+0.07) | +0.20 | 0.21% (0.13%) | ❌ FAIL |
| alpha_03_iv_term_structure | IV term structure (VIX3M/VIX − 1) | secondary | VIXY | +0.035 | +0.155 (+3.1) | +5.7% (+1.5) | -6.5% (+0.14) | +0.20 | 0.22% (0.05%) | fail |
| alpha_04_vrp | VRP (IV² − RV²) | primary | delta-hedged straddles (15 names) | -0.023 | -0.030 (-2.0) | -149.5% (-5.0) | -72.2% (-3.54) | +0.89 | 0.61% (3.00%) | ❌ FAIL |
| alpha_04_vrp | VRP (IV² − RV²) | secondary | 30d VIX futures | -0.090 | -0.023 (-0.5) | -8.1% (-0.5) | -16.2% (-0.05) | +0.06 | 0.07% (0.13%) | fail |
| alpha_05_iv_rank_percentile | IV percentile (252d) | primary | delta-hedged straddles (15 names) | -0.055 | -0.083 (-5.0) | -120.6% (-5.4) | -68.6% (-3.57) | +1.35 | 0.82% (3.00%) | ❌ FAIL |
| alpha_05_iv_rank_percentile | IV percentile (252d) | secondary | 30d VIX futures | -0.070 | -0.086 (-1.7) | -13.6% (-2.0) | -27.3% (-0.30) | -0.21 | -0.30% (0.13%) | fail |
| alpha_07_iv_dispersion | SPX implied correlation (COR3M) | primary | SPY | +0.107 | +0.112 (+2.2) | +2.0% (+0.9) | +2.3% (+0.22) | +0.25 | 0.11% (0.01%) | ❌ FAIL |
| alpha_07_iv_dispersion | SPX implied correlation (COR3M) | secondary | 30d VIX futures | -0.145 | -0.157 (-3.1) | +26.0% (+1.9) | +4.0% (+0.34) | +0.42 | 0.67% (0.13%) | fail |
| alpha_12_iv_momentum | IV momentum (5d) | primary | delta-hedged straddles (15 names) | -0.036 | -0.064 (-3.7) | -167.5% (-4.1) | -76.6% (-3.20) | +0.52 | 0.42% (3.00%) | ❌ FAIL |
| alpha_12_iv_momentum | IV momentum (5d) | secondary | 30d VIX futures | -0.099 | -0.076 (-1.5) | -2.5% (-0.2) | -10.3% (+0.04) | +0.23 | 0.15% (0.13%) | fail |

IC horizon: 5d forward return for timing tests, one 5-day period for cross-section tests. Break-even cost = OOS gross mean return / mean turnover: the cost per unit traded (fraction of notional; of straddle premium for the panel, round trip) at which the net return is zero. Grids: `results/validation/`. Charts: `figures/validation/`.

**Findings (2026-10-20): no alpha passes.**
- **IV mean reversion is real in option P&L but costs too much to trade weekly.** IV percentile (alpha_05) ranks next-week hedged-straddle returns across names (OOS IC −0.084, t −5.0) and earns +41%/yr gross (Sharpe 1.35), but needs round-trip straddle costs below 0.8% of premium. A lower-turnover version with real bid/ask is the next test.
- **Implied correlation (alpha_07) is the best lead.** On SPY it is just VIX-level timing. On VIX futures (secondary test) it beats VIX-level, futures-basis and always-short strategies by +26%/yr (t +1.9 OOS, +2.9 full sample), and it is not the futures basis in disguise. It needs a fresh pre-registered test on forward data before it can count.
- **alpha_03's term structure** is the futures basis in disguise (rejected 2026-10-18; confirmed by the pipeline).

## Alpha Development Workflow

1. **Hypothesis**: Write `notes.md` with the idea, why it should work, expected decay
2. **Compute**: Generate signal values on a universe of securities over time
3. **Rank**: Cross-sectionally rank instruments by signal strength
4. **Test**: Compute IC, IR, half-life of predictive power (`historical.py` → `run_historical.py`)
5. **Validate**: Pre-register a tradability test (`validation.py` → `run_validation.py`); only a pass counts as an alpha
6. **Document**: Record pass/fail, edge cases, look-ahead risks

## Key Files
- `common/ic_engine.py` — the single IC methodology used for all historical results
- `common/validation.py` — the single tradability test and pass rule; `common/instruments.py` — instruments and costs
- `common/history.py` — historical data (CBOE + yfinance), cached in `data/history/`
- `common/utils.py` — IC helpers and forward returns for live snapshots

## Notes
- All alphas must be tested against look-ahead bias
- Use forward-looking returns only (no peeking into future bars)
- Prefer daily resolution unless intraday alpha requires otherwise