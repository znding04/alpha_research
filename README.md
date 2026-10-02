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

| Signal | Folder | Description | Status |
|--------|--------|-------------|--------|
| **IV Rank** | `alpha_01_iv_rank/` | ATM IV vs median IV spread across liquid contracts | ✅ Active |
| **IV Skew Dynamics** | `alpha_02_iv_skew_dynamics/` | 25-delta put-call skew & term structure slope | ✅ Active |
| **IV Term Structure Slope** | `alpha_03_iv_term_structure/` | ATM IV curve slope (short vs long DTE) as mean-reversion signal | ✅ Active |
| **VRP (Variance Risk Premium)** | `alpha_04_vrp/` | IV² - RV² variance risk premium, cross-sectional equity premium signal | ✅ Active |
| **IV Rank Percentile** | `alpha_05_iv_rank_percentile/` | Current ATM IV percentile vs 1-year historical range (mean-reversion) | 🔄 Building history |
| **VRP Term Structure** | `alpha_06_vrp_term_structure/` | VRP slope & curvature across expirations (IV²-RV² term structure) | ✅ Active |
| **IV Dispersion** | `alpha_07_iv_dispersion/` | Index vs weighted constituent IV spread (dispersion trading signal) | 🔄 Building history |

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
