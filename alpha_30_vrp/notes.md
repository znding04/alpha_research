# Alpha 30 — VRP Signal (alpha_30_vrp)

## Hypothesis
The Variance Risk Premium (VRP) = implied variance (ATM IV²) minus realized variance (historical RV²). Positive VRP indicates options are expensive relative to recent realized vol; negative VRP indicates options are cheap.

## Signal Design
- Compute ATM implied volatility from nearest liquid expiration (DTE 7-60)
- Compute 20-day trailing realized vol from daily close prices (annualized std of log returns)
- Signal = ATM IV - realized vol

## Why This Works (Expected)
Equity options typically trade with IV > RV (positive VRP) due to risk premium. Large positive VRP suggests overpricing and potential mean-reversion downward; negative VRP suggests underpricing and potential rebound. We test cross-sectionally across the 6 tickers.

## Implementation Details
- Main script: `main.py`
- IC test script: `ic_analysis.py`
- Uses `yfinance` for option chains and price history (free, no paid API)
- Saves output to `data/vrp_alpha_30.csv`

## Results (latest run)
See `data/vrp_alpha_30.csv` for latest values. Most tickers show negative VRP (IV < RV) as of this snapshot, indicating options trading at a discount to recent realized volatility.
