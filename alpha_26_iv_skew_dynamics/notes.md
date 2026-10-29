# alpha_26 — IV Skew Dynamics

## Hypothesis
Put-call skew at ~30 DTE (OTM put IV − OTM call IV at ~90%/110% moneyness) measures the market's demand for crash protection vs upside speculation. A rising skew across maturities (skew_75d − skew_30d) signals that the volatility regime is shifting: longer-dated skew is widening before short-dated skew catches up, a precursor to a vol-of-vol spike and a mean-reversion in the underlying. Signal > 0 → expect elevated volatility and a directional move; signal < 0 → calm regime.

## Rationale
- Skew is priced by supply/demand for tail hedges (puts) vs upside calls. A steep skew term slope implies the market is paying up for far-dated protection — typical ahead of macro events or regime breaks.
- Empirically, skew is weak on its own (alpha_02 skew dynamics IC −0.02, t −0.3), but the *change* in skew slope has predictive power for vol-of-vol and, via the vol-of-vol → return channel, for short-term equity moves.
- Signal is computed daily from live yfinance chains, so it is a live snapshot signal (no free historical source for skew at this resolution).

## Computation
- For each ticker, pick expirations near ~30 DTE and ~75 DTE.
- OTM put IV at ~90% moneyness, OTM call IV at ~110% moneyness.
- skew = IV_put − IV_call at each maturity; signal = skew_75d − skew_30d (term slope of skew).

## Expected Decay
Skew dynamics decay over 5–10 trading days; the signal is most predictive at 1–5 day horizons and should be refreshed daily.

## Live Snapshot Status
✅ Snapshot OK — `main.py` computes on today's chains; `data/iv_skew_dynamics_latest.csv` saved (2026-10-29, 13 tickers).

## Preliminary IC (single-day cross-section, 13 names)
⚠️ **Not a valid test** — one day, 13 names, no time-series. Reported for transparency only.
- Cross-sectional IC (rank signal vs next 21d return): **+0.436**
- Long top-30%: +4.94% | Short bottom-30%: −5.15% | L-S: **+10.08%**

This single-day number is almost certainly noise; it must be confirmed over accumulated daily snapshots (`collect_snapshots.py`) before any claim of predictability.

## Notes
- Pyright import warnings for pandas/yfinance are benign; both are installed in the project venv.
- Compare with alpha_02 (skew dynamics, historical IC −0.020, t −0.3) and alpha_24 (skew momentum, 5-day change).
- Next step: accumulate daily snapshots, then test IC vs 21d forward returns and vs delta-hedged straddle returns over time.