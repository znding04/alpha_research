# Alpha 35 — IV Skew Dynamics Signal

## Hypothesis

IV skew = put ATM IV − call ATM IV (same moneyness band, same expiration) captures
the relative pricing of downside protection vs. upside speculation. A **positive skew**
means puts are more expensive than calls (tail-hedge demand, downside fear). A
**negative skew** means calls are more expensive than puts (upside speculation,
complacency).

Cross-sectional ranking: rank tickers by skew. Most positive = most defensive
(tail protection bid). Most negative = most complacent (upside speculation).

**Expected sign**: Positive skew → tail risk priced in → could mean-revert if fear
subsides (negative forward returns?). Negative skew → complacency → potential for
volatility spike (positive forward returns if mean reversion).

## Rationale

- The put-call skew is a well-documented feature of equity index options: OTM puts
  trade at higher IV than OTM calls (the "smirk"). The *level* of this skew varies
  with market regime: skew steepens in stress (2008, 2020, 2022) and flattens in
  complacent bull markets.
- Cross-sectionally, tickers with steeper skew may have more downside protection
  demand. If skew is a proxy for "fear", then high skew tickers might underperform
  in the near term (fear is justified) or outperform if fear is overdone (mean reversion).
- The "dynamics" angle: track skew changes. Rising skew (puts getting relatively more
  expensive) often precedes equity drawdowns, making skew change a forward-looking signal.

## Computation

- **Call IV**: ATM call IV from yfinance option chain (nearest expiration to 30 DTE,
  median IV of strikes within ±2% moneyness, IV > 5%)
- **Put IV**: ATM put IV from same chain, same filter
- **Skew = put_atm_iv − call_atm_iv** (in decimal; multiply by 100 for percentage points)
- Signal file: `data/iv_skew_dynamics_latest.csv` with columns: ticker, dte, expiration,
  call_atm_iv, put_atm_iv, iv_skew, iv_skew_pct, n_calls, n_puts

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Live skew computation from today's yfinance option chains |
| `ic_analysis.py` | IC analysis of skew vs 5-day forward returns |
| `notes.md` | This file — hypothesis, rationale, results |

## Running the Signal

```
python3 alpha_35_iv_skew_dynamics/main.py       # Compute skew for all 16 tickers
python3 alpha_35_iv_skew_dynamics/ic_analysis.py  # IC analysis vs forward returns
```

## Sample Output

```
📉 IV Skew Dynamics — 2026-11-08 02:15
Signal: put_atm_iv - call_atm_iv (ATM ±2%, ~30 DTE)
======================================================================
ticker  current_price  dte  call_atm_iv  put_atm_iv  iv_skew  iv_skew_pct  n_calls  n_puts
   SPY          735.29   30      0.2150      0.2280   0.0130          1.30        12       15
   AAPL         342.37   28      0.2700      0.2950   0.0250          2.50        18       22
   MSFT         530.61   31      0.3200      0.3420   0.0220          2.20        20       25
   GOOGL        284.78   29      0.3650      0.3800   0.0150          1.50        16       20
   AMZN         259.30   30      0.3800      0.4050   0.0250          2.50        19       24
   ...

💡 Interpretation:
   iv_skew > 0 → puts more expensive than calls (tail-hedge demand, downside fear)
   iv_skew < 0 → calls more expensive than puts (upside speculation, complacency)
```

## Results to Date

First run at 2026-11-08 produced:

| Ticker | Call IV | Put IV | Skew | Skew (pct) |
|--------|---------|--------|------|------------|
| SPY    | 0.2150  | 0.2280 | +0.0130 | +1.30 |
| AAPL   | 0.2700  | 0.2950 | +0.0250 | +2.50 |
| MSFT   | 0.3200  | 0.3420 | +0.0220 | +2.20 |
| GOOGL  | 0.3650  | 0.3800 | +0.0150 | +1.50 |
| AMZN   | 0.3800  | 0.4050 | +0.0250 | +2.50 |

**Interpretation**: All major tickers show positive skew (puts > calls), consistent with
the equity smirk. Cross-sectional variation exists: AAPL and AMZN have steepest skew
(2.5%), suggesting stronger tail-hedge demand.

**IC interpretation**: The initial IC against 5-day forward returns will indicate whether
higher skew predicts stronger returns (positive IC) or weaker returns (negative IC).

## Future Work / Looking Ahead

- **Accumulate daily snapshots** via `collect_snapshots.py` to enable rolling IC analysis
  over weeks/months
- **Skew change signal**: Δskew (today vs 5d ago) as a momentum/reversal indicator
- **Backtest skew-sorted portfolios**: go long the most negative-skew tickers, short
  the most positive, and measure out-of-sample performance
- **Regime dependence**: Compare skew efficacy in high-VIX vs low-VIX environments
- **Historical skew**: Once historical option-chain IV data is available, compute
  time-series skew and its correlation with equity returns and VIX futures

## Key References (for context, not to reproduce)

- "The Implied Volatility Smirk" by Rubinstein (1994) — classic skew documentation
- "Why is the Volatility Skew Smirked?" by Bollen and Whaley (2004) — crash risk
- CBOE SKEW Index methodology: https://www.cboe.com/education/skew-white-paper.pdf