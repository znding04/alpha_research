# Alpha 31 — IV Skew Dynamics (alpha_31_iv_skew_dynamics)

## Hypothesis
The put-call IV skew (25-delta put IV − 25-delta call IV) captures market fear/stress: lower/negative skew = more expensive puts (fear), higher/positive skew = more expensive calls (complacency). \n
We test whether changes in this skew predict forward returns via mean-reversion: rising fear (more negative skew) → potential bullish rebound; easing fear (less negative/positive skew) → potential bearish correction.

## Signal Design
- 25-delta Black-Scholes call/put Greeks at ~30‑50 DTE expirations (when available)
- Compute cross-sectional skew = put_25d_iv − call_25d_iv (positive = fear/stress)
- Rank tickers by skew (lower = more fear = higher mean-reversion expectation)
- Cross-sectional IC tests vs 5‑day forward returns

## Why This Works (Expected)
- Equity options exhibit put-call skew variations reflecting risk premiums
- Deep fear (large put premiums vs calls) tends to mean-revert upward (bullish returns)
- Deep complacency (large call premiums vs puts) tends to mean-revert downward (bearish returns)
- Alternative to pure IV signals (VRP, IV Rank) — focuses on skew shape rather than level

## Implementation Details
- **Main script**: `main.py` computes latest skew values for all universe tickers (SPY, QQQ, IWM, DIA, GLD, SLV, TLT, EEM, EWZ, FXI, GDX, USO, AAPL, MSFT, GOOGL, AMZN)
- **IC test script**: `ic_analysis.py` computes cross-sectional IC vs 5‑day forward returns
- Uses `yfinance` for option chains and price history (free, no paid API)
- Saves latest skew snapshot to `data/iv_skew_dynamics_latest.csv`
- Simplicity advantage over complex smile-fitting or term-structure approaches

## Results (latest run)
Current skew values serve as baseline for IC tests. Full IC analysis requires accumulating skew over multiple days to compute changes, but cross-sectional rank provides immediate signal.

## Validation Design
**Pre-registration:** Future validation will test: [1] In-sample (≤2018) IC of skew vs next 5‑day return; [2] Out-of-sample (2019‑2026) IC with sign as hypothesized; [3] Hedge-relevant IC against 30‑d delta‑hedged 30‑d ATM straddle returns; [4] Traditional alpha test (SPY with transaction costs vs equal‑weight short straddles).

## Related Signals
- alpha_02_iv_skew_dynamics: Cross-sectional skew across expirations (level)
- alpha_26_iv_skew_dynamics: 25Δ put-call skew term slope
- alpha_03_iv_term_structure: IV term structure slope (level)
- alpha_27_iv_term_refined: Normalized IV term structure slope

This signal isolates pure skew change rather than term structure or level signals.
