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
├── alpha_*/          # Individual alpha ideas (one folder per signal)
│   ├── main.py       # Signal computation
│   ├── ic_analysis.py  # Information coefficient tracking
│   └── notes.md      # Hypothesis, rationale, results
├── common/           # Shared utilities (factors, data loaders, IC calculators)
│   └── utils.py
├── data/             # Cached datasets (gitignored)
├── notebooks/        # Exploratory research
└── README.md         # This file
```

## Implemented Signals

**Status legend** (as of 2026-10-18):
- ✅ **Snapshot OK**: signal computes correctly for all 6 tickers on a live chain. **No alpha has a real IC yet**; that needs ≥30–60 trading days of daily snapshots.
- 🔄 **Needs history**: signal is a time-series change/rolling stat and cannot be computed until snapshot history accumulates.
- ⚠️ **Data issue**: depends on synthetic or placeholder history; outputs are not meaningful yet.

| Signal | Folder | Description | Status |
|--------|--------|-------------|--------|
| **IV Rank** | `alpha_01_iv_rank/` | ATM IV vs median IV spread across liquid contracts | ✅ Snapshot OK |
| **IV Skew Dynamics** | `alpha_02_iv_skew_dynamics/` | 25-delta put-call skew (Black-Scholes delta) at ~30d / ~75d & skew term slope | ✅ Snapshot OK (fixed 10-18) |
| **IV Term Structure Slope** | `alpha_03_iv_term_structure/` | ATM IV term structure slope & far/near ratio (also covers calendar spread) | ✅ Snapshot OK (fixed 10-18) |
| **VRP (Variance Risk Premium)** | `alpha_04_vrp/` | IV² - RV² variance risk premium, cross-sectional equity premium signal | ✅ Snapshot OK |
| **IV Rank Percentile** | `alpha_05_iv_rank_percentile/` | Current ATM IV percentile vs 1-year historical range (mean-reversion) | ⚠️ 260/261 history days synthetic |
| **VRP Term Structure** | `alpha_06_vrp_term_structure/` | VRP slope & curvature across expirations (also covers VRP carry) | ✅ Snapshot OK |
| **IV Dispersion** | `alpha_07_iv_dispersion/` | Index vs weighted constituent IV spread (dispersion trading signal) | 🔄 Needs history |
| **Gamma Exposure (GEX)** | `alpha_08_gamma_exposure/` | Net dealer gamma exposure from OI; zero-gamma flip level | ✅ Snapshot OK (fixed 10-18) |
| **IV Surface Curvature** | `alpha_09_iv_surface_curvature/` | Quadratic OTM smile fit & 25Δ butterfly at ~30 DTE | ✅ Snapshot OK (fixed 10-18) |
| **Vol-of-Vol** | `alpha_11_vol_of_vol/` | Realized vol of ATM IV (20d rolling); regime stability & transition risk signal | 🔄 Needs history (20d) |
| **IV Momentum** | `alpha_12_iv_momentum/` | 5-day ATM IV trend (% change); fear spikes vs complacency signal | ⚠️ History is placeholder IVs, rebuild |
| **IV Skew Momentum** | `alpha_13_iv_skew_momentum/` | 5-day rate of change of 25-delta put-call skew | 🔄 Needs history |
| **Put/Call OI-Weighted IV Spread** | `alpha_14_iv_smile_asymmetry/` | Volume/OI-weighted put-call IV spread & put/call ratios | ✅ Snapshot OK |
| **IV Term Structure Momentum** | `alpha_15_iv_term_momentum/` | Rate of change of IV term structure slope | 🔄 Needs history |
| **IV Skew Convexity** | `alpha_16_iv_skew_convexity/` | Tail butterfly convexity (10Δ/5Δ wings) at ~30 DTE | ✅ Snapshot OK (fixed 10-18) |
| **IV Surface Skewness** | `alpha_19_iv_surface_skewness/` | 3rd/4th moments of IV smile across strikes; risk-neutral tail risk | ✅ Snapshot OK |
|| **VRP Skew** | `alpha_20_vrp_skew/` | Put VRP minus Call VRP (IV²-RV² asymmetry) | ⚠️ IC uses synthetic back-filled history |
|| **IV Change** | `alpha_22_iv_change/` | 5-day ATM IV change (contrarian mean-reversion) across liquid expirations | ⚠️ Requires ≥2 snapshots for change |

**Removed duplicates (2026-10-18):** `alpha_10_vrp_carry` (near−far VRP = VRP term slope, covered by alpha_06), `alpha_17_iv_calendar_spread` (short−long ATM IV = term slope, covered by alpha_03), `alpha_21_iv_percentile` (near-identical copy of alpha_05 writing the same history file), `alpha_18_vrp_momentum` (despite the name, its "momentum" is near VRP − mid VRP at one point in time, i.e. the VRP term slope covered by alpha_06). Numbers are not reused.

**IC methodology:** `ic_analysis.py` scripts use `common.utils.forward_return()`, i.e. returns *after* the signal snapshot date. Before 2026-10-18 they used the past 5-day return. The simulated rolling-IC sections are synthetic demos with the IC built in and are **not evidence** of predictive power.

## Alpha Development Workflow

1. **Hypothesis**: Write `notes.md` with the idea, why it should work, expected decay
2. **Compute**: Generate signal values on a universe of securities over time
3. **Rank**: Cross-sectionally rank instruments by signal strength
4. **Test**: Compute IC, IR, half-life of predictive power
5. **Document**: Record pass/fail, edge cases, look-ahead risks

## Key Files
- `common/utils.py` — shared helpers for IC calculation, rolling statistics, factor cleaning

## Notes
- All alphas must be tested against look-ahead bias
- Use forward-looking returns only (no peeking into future bars)
- Prefer daily resolution unless intraday alpha requires otherwise