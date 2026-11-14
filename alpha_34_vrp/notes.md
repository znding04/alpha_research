# Alpha 34 — VRP (Variance Risk Premium) Signal

## Hypothesis

VRP = IV² − RV² should predict cross-sectional returns. A **positive VRP** means implied vol is
squared above realized vol (vol is expensively priced relative to future realization). A
**negative VRP** means implied vol is below realized vol (vol is cheap, upward pressure on IV).

Cross-sectional ranking: rank tickers by VRP. Most positive = most expensive vol
(underweight). Most negative = most fearful vol (overweight / mean-reversion long).

**Expected sign**: VRP > 0 → short vol premium (as in VIX futures carry); VRP < 0 → long vol
(possible mean-reversion if IV^2 reverts toward RV^2).

## Rationale

- VRP captures the market price of variance risk. Historically, the VRP tends to be positive
  (IV > RV), meaning options are expensive relative to future realized vol. This is the
  "vol premium" analog of the equity risk premium.
- A positive VRP should predict **lower** forward returns (inverse relationship: expensive vol
  → lower expected returns), or potentially **higher** if the market prices vol risk as a premium
  for bearing tail risk.
- A negative VRP should predict **higher** forward returns (vol is cheap, room for IV to rise).
- Cross-sectionally: when many tickers have positive VRP, it may signal broad-based vol
  complacency; when negative, broad-based vol anxiety.

## Computation

- **IV**: ATM implied volatility from yfinance option chain (nearest expiration to 30 DTE)
- **RV**: 30-day annualized realized volatility from yfinance daily close-to-close log returns
- **VRP = IV² − RV²** (both in decimal; multiply by 10000 for basis points)
- Signal file: `data/vrp_alpha_34_latest.csv` with columns: ticker, dte, atm_iv, realized_vol,
  iv_squared, rv_squared, vrp, vrp_pct

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Live VRP computation from today's yfinance option chains |
| `ic_analysis.py` | IC analysis of VRP vs 5-day forward returns |
| `notes.md` | This file — hypothesis, rationale, results |

## Running the Signal

```
python3 alpha_34_vrp/main.py       # Compute VRP for all 16 tickers
python3 alpha_34_vrp/ic_analysis.py  # IC analysis vs forward returns
```

## Sample Output

```
📊 VRP (Variance Risk Premium) — 2026-11-07 02:02
======================================================================
ticker  current_price  atm_iv  realized_vol  iv_squared  rv_squared  vrp  vrp_pct
   SPY          735.29  0.1799      0.2014   0.032363    0.040566  -0.008203  -82.03
   AAPL         342.37  0.2329      0.2512   0.054236    0.063100  -0.008864  -88.64
   MSFT         530.61  0.2763      0.2725   0.076344    0.074256   0.002088   20.88
   GOOGL        284.78  0.3178      0.3032   0.100997    0.091930   0.009067   90.67
   AMZN         259.30  0.3289      0.3167   0.108171    0.100294   0.007877   78.77
   ...

💡 Interpretation:
   VRP > 0 → positive variance risk premium (IV^2 > RV^2, expensively priced vol)
   VRP < 0 → negative variance risk premium (IV^2 < RV^2, cheap vol)
```

## Results to Date

This is a new signal (alpha_34_vrp). The first run at 2026-11-07 produced:

- **SPY**: VRP = −82.03 bp (IV² < RV²; vol cheap, room for mean reversion higher)
- **AAPL**: VRP = −88.64 bp (vol cheap relative to realized)
- **MSFT**: VRP = +20.88 bp (IV² > RV²; vol expensive)
- **GOOGL**: VRP = +90.67 bp (IV² > RV²; vol expensive)
- **AMZN**: VRP = +78.77 bp (IV² > RV²; vol expensive)

**IC interpretation**: The initial IC against 5-day forward returns will indicate whether
higher VRP predicts stronger returns (positive IC) or weaker returns (negative IC). A
significant negative IC would be consistent with the "expensive vol → lower returns" story,
while a positive IC would suggest the market prices the vol risk as a premium.

## Future Work / Looking Ahead

- **Accumulate daily snapshots** via `collect_snapshots.py` to enable rolling IC analysis
  over weeks/months
- **Compare VRP sign across regimes** (high VRP vs low VRP periods) to check for regime
  dependence
- **Backtest VRP-sorted portfolios**: go long the most negative-VRP tickers, short the most
  positive, and measure out-of-sample performance
- **Historical VRP**: Once historical option-chain IV data is available, compute time-series
  VRP and its correlation with equity returns and VIX futures term structure
- **Roll-forward IC**: After 30+ daily snapshots, run rolling IC to assess persistence

## Key References (for context, not to reproduce)

- "The Variance Risk Premium" by Buss and Vilhuber (2012) — classic VRP literature
- "Equity Volatility and Variance Risk Premia" by Bollerslev, Todorov, and Li (2015)
- CBOE VIX shape and VRP dynamics: https://www.cboe.com/education/vix-sp-white-paper.pdf