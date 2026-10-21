# VRP Change (alpha_21_vrp) — Signal Notes

**Created:** 2026-10-21  
**Type:** Cross-sectional / time-series (change-based)  
**Data source:** Live yfinance option chains + 30-day realized vol (historical prices)  
**Status:** ✅ Snapshot computes; 🔄 Needs 2+ days of history for change

## Hypothesis

The **change** in Variance Risk Premium (ΔVRP = VRP_today − VRP_yesterday) carries predictive information for forward returns, beyond the level of VRP itself. Rapid increases in VRP (fear spike) tend to precede short-term mean reversion; rapid decreases (complacency) tend to precede continuation or risk buildup.

- `ΔVRP > 0` → Options getting more expensive relative to realized vol (fear rising) → potential near-term reversal
- `ΔVRP < 0` → Options cheapening relative to RV (fear falling) → trend continuation

The change metric avoids the earnings-contamination problem that affects VRP level (alpha_04) because earnings events tend to shift both IV and RV simultaneously, reducing the change magnitude.

## Signal Definition

| Step | Rule |
|------|------|
| Expiration | Nearest liquid expiry within 7–60 DTE |
| Liquidity filter | `volume > 10` OR `openInterest > 100`; `IV > 0.05`; `IV < 3.0` |
| ATM IV | Robust median of strikes within ±2% of spot (same method as alpha_12) |
| RV | 30-day annualized std(log returns) from yfinance close history |
| VRP | `IV² − RV²` (variance risk premium) |
| Signal | `ΔVRP_1d` = VRP(today) − VRP(yesterday), tracked in JSON history |

## Implementation

- `main.py`: Computes current VRP, writes to `data/vrp_change_latest.csv` and `data/vrp_change_history.json`
- `ic_analysis.py`: Loads latest CSV + JSON history, computes synthetic rolling IC, and tests 5-day forward returns
- Uses same ATM-IV method (`get_robust_atm_iv`) as alpha_12 to avoid placeholder-IV issues

## Caveats and Next Steps

- First-day change is `NaN`; second-day onwards it becomes valid (`vrp_change_1d`)
- Requires daily collection (cron or manual) to accumulate history; full rolling IC requires ≥30 days
- Uses nearest expiration, ignoring term structure (same limitation as alpha_04)
- Not yet validated against delta-hedged straddles or VIX futures (see alpha_04 for the pre-registered design pattern)

## Files

- `main.py` — live VRP + change computation + JSON history tracker
- `ic_analysis.py` — single-snapshot forward-return IC + synthetic demo
- `notes.md` — this file
- `data/vrp_change_latest.csv` — latest signal snapshot
- `data/vrp_change_history.json` — running history for momentum computation
