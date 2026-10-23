# Put-Call Parity Residual (alpha_22)

## Hypothesis

Put-call parity violations signal hard-to-borrow or easy-borrow regimes:

- **Positive residual** (C - P > S - K*e^{-rT}): implied forward > spot-forward → puts cheap or calls rich relative to parity. For American puts on dividend payers, this suggests the underlying is hard-to-borrow (sheltered cash) → **short-bias signal**.
- **Negative residual**: opposite → likely crowded long / easy borrow → long-bias.

Cross-sectionally, tickers with the largest absolute residual should outperform because parity deviations are arbitrageable (in part) and signal directional pressure.

## Why This Signal Differs from IV-Based Alphas

All existing alphas use `impliedVolatility` — a model-derived estimate. This alpha uses actual traded mid prices. Parity must hold in efficient markets; deviations indicate:

1. **Borrow constraints**: hard-to-borrow stocks have elevated cost-of-carry, raising put prices relative to calls.
2. **Dividend timing** : early exercise premium on American options.
3. **Local supply/demand imbalances**: dealer inventory, spot vs. futures pricing.

These effects are orthogonal to the IV surface; a stock can have "normal" IV but still be hard-to-borrow.

## Signal Definition

| Component | Description |
|-----------|-------------|
| `call_mid` | Bid-ask midpoint (lastPrice fallback) for ATM call |
| `put_mid` | Same for ATM put |
| `K` | Strike with maximum liquidity having both call and put |
| `r` | 13-week T-bill from ^IRX |
| `q` | Dividend yield from ticker.info |
| `parity_bps` | 10000 × (C - P - S + Ke^{-(r-q)T}) / S |

## Files

- `main.py`: compute parity_bps for live option chains
- `ic_analysis.py`: single-period IC vs 5-day forward returns

## Results

*To be filled after running `python3 alpha_01_iv_rank/main.py` and `python3 alpha_21_put_call_parity/ic_analysis.py`.*

## Caveats

1. **American options**: Early exercise premium on puts can cause positive residuals even without borrow cost.
2. **Liquidity filter**: Only strikes with `volume > 10` or `OI > 100` on BOTH legs are used. This may miss illiquid underlyings.
3. **Market hours**: yfinance returns stale IV/quote data after-hours. IV levels above 1.0 or below 0.05 indicate stale data and are filtered.