# IV Skew Dynamics (25-delta Risk Reversal) — Alpha Signal Notes

## Hypothesis

**The 25-delta put-call risk reversal (RR25 = IV_put(25Δ) − IV_call(25Δ)) encodes the market's directional volatility bias, and changes in that bias predict forward returns.**

### Rationale

1. **Skew is the "fear" signal.** OTM puts richer than OTM calls (RR25 > 0) is the classic equity smile shape: investors pay for crash protection. A flattening or call-skewed smile (RR25 → 0 or negative) signals complacency.
2. **Skew dynamics.** A steepening skew (RR25 rising) coincides with rising tail-hedge demand — usually ahead of or during stress. A flattening skew coincides with calm, often a mean-reversion setup.
3. **Cross-sectional rank.** Ranking the core 16 tickers by RR25 isolates relative skew mispricing between instruments driven by the same macro factor. The hypothesis is that a steepening skew predicts negative forward returns (fear → mean reversion), while a flattening skew predicts positive returns.

## Signal Definition

| Step | Rule |
|------|------|
| Expiration | Nearest expiry within 10 DTE of 30 DTE (skip weekly noise / 0-DTE) |
| Liquidity filter | `volume > 10` OR `openInterest > 100`; `0.01 < IV < 3.0`; `lastPrice > 0`; ≥5 calls + ≥5 puts |
| ATM IV | Median IV of strikes within ±2% moneyness (IV > 5%) |
| 25δ strikes | Black-Scholes delta solved by root-finding on the strike, with IV interpolated from the chain; fallback to 5% OTM put/call strike if solve fails |
| **RR25** | `IV_put(25Δ) − IV_call(25Δ)` |
| 5d change | `rr_change_5d = RR25_today − RR25_5d_ago` (from `data/iv_skew_dynamics_42_history.json`) |

### Interpretation

- `RR25 > 0` → put skew (fear / tail-hedge demand)
- `RR25 < 0` → call skew (complacency / upside demand)
- `rr_change_5d > 0` → skew steepening (rising fear)
- `rr_change_5d < 0` → skew flattening (falling fear)

## Data Source & Limitations

**Source:** yfinance option chains (nearest ~30 DTE expiry) + daily price history for forward returns.

**Limitations:**

1. **yfinance IV quality** — placeholder IVs (e.g. 0.0625) appear frequently, especially for near-term expirations; guards like `IV > 0.01` and `IV > 0.05` for ATM are applied but cannot eliminate all noise.
2. **Delta solve sensitivity** — the 25-delta strike is found by scanning available strikes and evaluating BS delta at each; a 0.10 delta tolerance is used. When the chain is thin (few strikes), the fallback to a 5% OTM strike is used, which may differ from the true 25-delta strike.
3. **Single snapshot** — IC analysis requires accumulated daily snapshots from `collect_snapshots.py`; a single-day IC is noise.
4. **16 tickers** — enough for a rank IC but below the 10-observation minimum in `compute_ic`; treat single-day IC as descriptive only.
5. **History file** — `data/iv_skew_dynamics_42_history.json` persists daily RR25 levels; the 5-day change is computed from real snapshots once enough days accumulate.

## Files

- `main.py` — computes the signal, writes `data/iv_skew_dynamics_42_latest.csv` and updates `data/iv_skew_dynamics_42_history.json`
- `ic_analysis.py` — single-snapshot IC + synthetic rolling-IC demo (not evidence of predictability)

## Next Steps

1. Accumulate daily snapshots via `collect_snapshots.py`
2. Compute rolling IC (≥60 trading days)
3. Test pre-registered tradability on SPX VIX futures or delta-hedged straddles (see `run_validation.py`)