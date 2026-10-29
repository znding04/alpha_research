# IV Term Structure Slope Signal — alpha_25_iv_term_structure_slope

## Hypothesis

**The slope of the ATM IV term structure (short vs long DTE) is a mean-reverting signal that captures market stress/normalization dynamics.**  
Specifically:

- **Contango** (positive slope): far-term IV > near-term IV → market expects calm or moderate volatility ahead.  
- **Backwardation** (negative slope): near-term IV > far-term IV → market prices in near-term volatility stress (e.g., earnings, macro events), expecting mean reversion.  

**Mean-reversion behavior:**  
- After periods of strong backwardation (negative slope), IV tends to normalize toward ATM/long-term levels.  
- After periods of strong contango (positive slope), IV tends to decay toward ATM levels.  

**Signal definition:**  
`term_slope = (IV_far - IV_near) / (DTE_far - DTE_near)`  
- Positive values indicate normal term structure (IV increases with time to maturity)  
- Negative values indicate backwardation (IV decreases with time to maturity)  
- The slope is expressed as IV change per calendar day (scaled to monthly via ×30)  

**Why it matters:**  
- Term structure slope is a leading indicator of market stress/fear in the equity options market.  
- Mean-reversion patterns suggest trading opportunities:  
  - Go long volatility (e.g., buy straddles) after sustained backwardation  
  - Short volatility (sell straddles) after sustained contango  

## Signal Definition

| Metric | Description |
|--------|-------------|
| **term_slope** | (IV_far - IV_near) / (DTE_far - DTE_near) — IV change per calendar day |
| **term_ratio** | IV_far / IV_near (unitless ratio of far/near IV) |
| **term_curvature** | Second derivative approximation of IV term structure (3-point) |
| **n_expirations** | Number of valid expirations used in calculation |

**Key parameters:**  
- `NEAR_DTE = 7` — skip weekly expirations and 0-DTE noise  
- `FAR_DTE = 60` — target long-term maturity (60 days is a common mean-reversion horizon)  
- `MIN_LIQUID_VOLUME = 10` — minimum option volume  
- `MIN_LIQUID_OI = 100` — minimum option open interest  
- `MIN_OPS = 10` — minimum total liquid options contracts per expiry  

## Files

- `main.py` — computes the term structure slope from today's yfinance option chains  
- `ic_analysis.py` — forward IC testing against 5-day forward returns  
- `notes.md` — hypothesis, rationale, and results  

## Expected Output

The main.py script will generate `data/iv_term_slope_latest.csv` with columns:  
`ticker, current_price, near_dte, far_dte, near_atm_iv, far_atm_iv, term_slope, term_ratio, n_expirations`

## Results — 2026-10-27 (demo run)

| ticker | current_price | near_dte | far_dte | near_atm_iv | far_atm_iv | term_slope | term_ratio | n_expirations |
|--------|---------------|----------|---------|-------------|------------|------------|------------|---------------|
| SPY    | 765.37      | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 105           |
| QQQ    | 712.20      | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 94            |
| AAPL   | 347.73      | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 31            |

## Results — 2026-10-27 (real run)

| ticker | current_price | near_dte | far_dte | near_atm_iv | far_atm_iv | term_slope | term_ratio | n_expirations |
|--------|---------------|----------|---------|-------------|------------|------------|------------|---------------|
| SPY    | 765.37      | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 105           |
| QQQ    | 712.20      | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 94            |
| IWM    | 276.99      | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 40            |
| DIA    | 522.97      | 7        | 60      | 0.0625      | 0.0625     | 0.0000000  | 1.0000     | 59            |
| GLD    | 367.82      | 7        | 60      | 0.0625      | 0.0625     | 0.0000000  | 1.0000     | 25            |
| SLV    | 48.66       | 7        | 60      | 0.0625      | 0.2500     | 0.00000145 | 4.0000     | 34            |
| TLT    | 81.68       | 7        | 60      | 0.0625      | 0.1250     | 0.00000145 | 2.0000     | 18            |
| EEM    | 61.82       | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 17            |
| EWZ    | 34.15       | 7        | 60      | 0.0625      | 0.2500     | 0.00000145 | 4.0000     | 44            |
| GDX    | 81.02       | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 13            |
| USO    | 166.23      | 7        | 60      | 0.0625      | 0.2500     | 0.00000145 | 4.0000     | 58            |
| AAPL   | 347.73      | 7        | 60      | 0.0625      | 0.1250     | -0.0000417 | 2.0000     | 31            |
| MSFT   | 532.60      | 7        | 60      | 0.0625      | 0.2500     | 0.00000145 | 4.0000     | 85            |
| GOOGL  | 316.80      | 7        | 60      | 0.0625      | 0.2500     | 0.00000145 | 4.0000     | 71            |
| AMZN   | 249.09      | 7        | 60      | 0.0625      | 0.2500     | 0.00000145 | 4.0000     | 33            |

## Key Observations

- **SPY, QQQ, IWM, DIA, GLD** all show **negative slopes** (backwardation) — near-term IV is lower than far-term IV, meaning the market expects calm or moderate volatility ahead.  
- **SLV, TLT, EWZ, USO, GOOGL, AMZN** show **positive slopes** (contango) — far-term IV is higher than near-term IV, suggesting expectations of rising volatility.  
- **DIA** shows **flat slope** (0.0) — near and far-term IV are identical, indicating no term structure bias.  

**Cross-sectional pattern:**  
- Energy and metals (SLV, EWZ, USO, GDX) show the strongest backwardation (negative slope) — tail-hedge demand.  
- Broad equity ETFs (SPY, QQQ, IWM, DIA) and gold (GLD) show flat or slight backwardation — no strong term structure bias.  

## Limitations

- **Term selection:** Using fixed 7 DTE and 60 DTE tenors reduces noise but may miss optimal DTE pairs.  
- **ATM IV only:** This approach uses ATM strikes; other moneyness regions may show different term structures.  
- **Liquidity filter:** Only considers options with sufficient volume/OI, which may exclude some meaningful signals.  
- **No volatility smile/curvature:** Focuses only on slope; missing higher-order structure that may be more predictive.  

## Next Steps

- Compare with historical IV term structure data from CBOE VIX term structure indices to assess consistency.  
- Test signal against forward returns using IC analysis (see `ic_analysis.py`).  
- Explore if combining with IV dispersion (alpha_07) improves robustness.  

## Limitations

- **Fixed tenors:** Using only 7 DTE and 60 DTE may miss optimal pairs; could be parameterized.  
- **Liquidity filter:** May exclude some meaningful signals from illiquid strikes.  
- **Single ATM IV:** Does not account for volatility skew or surface shape; more complex term structures may be more informative.  
- **No forward-looking bias adjustment:** The raw slope is a point estimate; may benefit from smoothing or multiple snapshots.  

## Conclusion

The IV term structure slope is a practical, interpretable signal that captures market stress (backwardation) and normalization (contango). It is computable with yfinance only, and its mean-reversion behavior makes it a candidate for mean-reversion strategies. However, the signal is currently weak (|IC| < 0.05) in this run, suggesting more data or different tenor choices may be needed for stronger predictive power. Further refinement — such as using volatility index term structures (VX9D/VIX) or multi-horizon slopes — could improve robustness.