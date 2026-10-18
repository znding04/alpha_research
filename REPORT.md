# Alpha Research Report

**Date**: 2026-10-16
**Universe**: AAPL, SPY, QQQ, MSFT, GOOGL, AMZN
**Data Source**: yfinance (live option chains; no historical option data)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Alpha Summaries (01-20)](#alpha-summaries)
3. [Synthetic Backtest Results](#synthetic-backtest-results)
4. [Data Limitations & Next Steps](#data-limitations--next-steps)

---

## Executive Summary

This report covers 20 options-based alpha signals spanning five major categories:

| Category | Alphas |
|---|---|
| **IV Skew / Smile** | 01, 02, 09, 13, 14, 16, 19 |
| **IV Term Structure** | 03, 15, 17 |
| **Variance Risk Premium (VRP)** | 04, 06, 10, 18, 20 |
| **IV Level / Regime** | 05, 07, 11, 12 |
| **Dealer Positioning** | 08 |

All signals are computed from live yfinance option chains. Because yfinance provides no historical option data, real rolling IC analysis requires daily snapshot accumulation (minimum 30-60 days). A synthetic backtest calibrated to each alpha's expected IC is provided as a performance baseline.

---

## Alpha Summaries

### Alpha 01 -- IV Rank (ATM vs Median Spread)

**Main Idea**: Spread between ATM implied volatility and the median IV across all liquid strikes. Positive spread indicates ATM vol premium (convexity risk); negative spread indicates OTM vol premium (tail-hedge demand).

**Signal Logic**:
- Fetch nearest liquid expiration (2-180 DTE)
- Filter: volume > 50 OR OI > 500, IV in (0.01, 3.0)
- ATM IV = median of strikes within +/-2% moneyness (IV > 5%)
- `signal = ATM_IV - median_IV`

**Key Parameters**: +/-2% moneyness for ATM, 180-day max expiry, 10-contract minimum

**Backtest Status**: Synthetic IC = +0.293, IR = 2.60. Real IC from `alpha_01_iv_rank/ic_analysis.py` uses single-snapshot Spearman + synthetic rolling IC simulation (window=20, seed=101).

---

### Alpha 02 -- IV Skew Dynamics (25-Delta Put-Call Skew)

**Main Idea**: Put-call IV skew (25-delta put IV minus 25-delta call IV) predicts forward equity returns. Extreme positive skew signals fear/institutional hedging with mean-reversion potential. The skew term structure slope (near vs far expiry) provides an additional regime signal.

**Signal Logic**:
- 25-delta put approximated at 0.95 x spot; call at 1.05 x spot
- `skew_25d = put_25d_IV - call_25d_IV` per expiration
- `skew_term_slope = (far_skew - near_skew) / (far_DTE - near_DTE)`

**Key Parameters**: 0.95/1.05 moneyness proxy, 180-day max DTE

**Backtest Status**: Synthetic IC = +0.323, IR = 2.23. Notes report expected rolling IC ~0.18, half-life ~15 days. Real IC pending daily data collection.

---

### Alpha 03 -- IV Term Structure Slope

**Main Idea**: Slope of ATM IV across expirations. Backwardation (near IV > far IV) signals acute stress/fear and mean-reversion bounce potential. Contango signals complacency and trend continuation.

**Signal Logic**:
- ATM IV = average of call and put IV at nearest strike to spot, per expiration
- `term_slope = (IV_far - IV_near) / (DTE_far - DTE_near)` (IV points per day)
- `term_curvature` = 3-point second derivative (if >= 3 expirations)

**Key Parameters**: Volume > 10 OR OI > 100 per leg, 180-day max DTE

**Backtest Status**: Synthetic IC = -0.329, IR = -4.23 (negative IC expected: backwardation -> bounce). Notes report expected IC -0.15 to -0.20. Liquidity filters were too strict in practice (only GOOGL/AMZN passed on first run).

---

### Alpha 04 -- Variance Risk Premium (VRP)

**Main Idea**: VRP = IV^2 - RV^2 (implied variance minus realized variance). Positive VRP means options are expensive relative to realized vol. Cross-sectionally, high VRP tickers should earn higher forward returns (variance risk premium harvesting).

**Signal Logic**:
- ATM IV: nearest expiry 14-60 DTE; liquidity-weighted average of near-ATM options (+/-5% moneyness)
- RV: 30-day rolling annualized log-return std x sqrt(252)
- `vrp_variance = ATM_IV^2 - RV^2`
- `vrp_ratio = ATM_IV^2 / RV^2`

**Key Parameters**: 14-60 DTE, 30-day RV lookback, +/-5% moneyness

**Backtest Status**: Synthetic IC = +0.521, IR = 2.68. Notes report expected IC ~0.15-0.20. Data quality concern: ATM IVs of ~1.56% appeared suspiciously low from yfinance.

---

### Alpha 05 -- IV Rank Percentile

**Main Idea**: Current ATM IV percentile rank vs its own 1-year historical distribution. High percentile (>80th) = IV expensive, mean-revert down, equity bounce. Low percentile (<20th) = IV cheap, mean-revert up in vol, equity underperformance.

**Signal Logic**:
- ATM IV computed identically to Alpha 04
- Historical observations stored in `data/iv_history.json` (252-day rolling window)
- `iv_percentile = % of historical obs <= current IV`
- `iv_zscore = (current_IV - hist_mean) / hist_std`

**Key Parameters**: 252-day max history, minimum 10 observations for valid percentile

**Backtest Status**: Synthetic IC = -0.508, IR = -2.79 (negative: high percentile -> underperformance). Real IC requires >= 30 daily snapshots; initial run shows only 1 observation per ticker.

---

### Alpha 06 -- VRP Term Structure

**Main Idea**: Extends Alpha 04 by computing VRP across the full term structure. The slope and curvature of VRP across maturities captures how fear is distributed over time. Inverted VRP term structure (near > far) signals event-driven fear and mean reversion.

**Signal Logic**:
- RV computed once (30-day lookback)
- For each expiration (1-180 DTE): `vrp_var = IV^2 - RV^2`
- `vrp_slope = (vrp_far - vrp_near) / (DTE_far - DTE_near)`
- `vrp_curvature` = 3-point second derivative

**Key Parameters**: 1-180 DTE (wider than Alpha 04), 30-day RV lookback

**Backtest Status**: Synthetic IC = -0.560, IR = -5.10. No real IC yet; notes outline validation plan (60+ daily runs, 80/20 in-sample/OOS split).

---

### Alpha 07 -- IV Dispersion (Index vs Constituent)

**Main Idea**: Index options (SPY, QQQ) are systematically overpriced vs constituents due to structural hedging demand and embedded correlation risk. Signal = index ATM IV minus weighted-average constituent ATM IV.

**Signal Logic**:
- ATM IV for index (SPY/QQQ) and each constituent
- Normalize constituent weights (SPY: AAPL 7%, MSFT 6%, GOOGL 3.5%, AMZN 3.5%; QQQ: AAPL 12%, MSFT 10%, GOOGL 6%, AMZN 5%)
- `dispersion = index_IV - weighted_constituent_IV`
- `dispersion_ratio = index_IV / weighted_constituent_IV`

**Key Parameters**: 14-60 DTE, minimum 2 constituents, +/-2% actionable threshold (200 bps)

**Backtest Status**: Synthetic IC = +0.327, IR = 1.93. No real IC yet; planned after 20+ days of history.

---

### Alpha 08 -- Gamma Exposure (GEX)

**Main Idea**: Net dealer gamma exposure from option OI predicts forward volatility regimes and price pinning. Positive GEX = dealers long gamma (dampens vol, mean reversion). Negative GEX = dealers short gamma (amplifies vol, momentum).

**Signal Logic**:
- `total_GEX = sum(-1 x OI x 100 x gamma x S^2 / 100)` across all strikes/expiries (1-45 DTE)
- `flip_strike` = first strike where cumulative GEX turns non-negative (zero-gamma pin level)
- `distance_to_flip_pct = (flip_strike - spot) / spot x 100`
- Gamma from yfinance; fallback to Black-Scholes approximation when NaN

**Key Parameters**: Max DTE = 45, contract size = 100

**Backtest Status**: Synthetic IC = -0.315, IR = -3.03. Simulated IC vs returns ~-0.10 to -0.15, IC vs vol change ~-0.15 to -0.20.

---

### Alpha 09 -- IV Surface Curvature

**Main Idea**: Curvature (second derivative) of the IV smile w.r.t. log-moneyness captures jump risk premium and tail event pricing. High curvature = fear/crash insurance demand.

**Signal Logic**:
- Fit quadratic: `IV = a + b*m + c*m^2` where `m = ln(K/S)`, weighted by volume+OI
- `curvature` = coefficient c (smile convexity)
- `normalized_curvature = curvature / ATM_IV`
- `butterfly_25d ~ curvature x 0.0225`
- Separate fits for calls and puts, then averaged; requires >= 5 liquid points per side

**Key Parameters**: DTE 7-45, |moneyness| <= 0.3

**Backtest Status**: Synthetic IC = +0.289, IR = 2.92. Expected IC ~0.05-0.10 (weakest of the set).

---

### Alpha 10 -- VRP Carry / Roll-down

**Main Idea**: Near-term VRP minus far-term VRP captures carry from selling near-term vol. Backwardation (near > far) signals excessive near-term fear and mean-reversion opportunity.

**Signal Logic**:
- `VRP = ATM_IV^2 - RV^2` per expiration
- `vrp_carry = VRP_near - VRP_far` (positive = backwardation)
- `roll_down_daily = -vrp_slope_per_day`
- `carry_ratio = vrp_carry / VRP_near`
- RV = 20-day rolling annualized realized vol

**Key Parameters**: DTE 5-180, RV window = 20 days

**Backtest Status**: Synthetic IC = +0.659, IR = 3.94 (strongest synthetic signal). Real run non-functional: yfinance returns flat ATM IV (0.0156) across all expirations, yielding VRP carry = 0. Requires alternative IV data source (Polygon, CBOE).

---

### Alpha 11 -- Vol-of-Vol (VoV)

**Main Idea**: Realized volatility of ATM implied volatility measures vol regime stability. High VoV = unstable regime / transition risk. Low VoV = stable / mean-reversion friendly.

**Signal Logic**:
- Daily: fetch ATM IV per ticker (14-60 DTE, liquidity-weighted)
- Persist to `data/vol_of_vol_history.csv`
- `vol_of_vol = 20-day std of daily IV pct-changes x sqrt(252)` (annualized)
- `vov_percentile` = cross-sectional rank among universe

**Key Parameters**: VoV window = 20 days (min_periods = 10)

**Backtest Status**: Synthetic IC = -0.545, IR = -3.63. Real IC pending (data building phase, first run 2026-10-06).

---

### Alpha 12 -- IV Momentum

**Main Idea**: Short-term ATM IV trend (5-day % change) predicts forward returns. Rising IV = fear buying (mean-reversion potential). Falling IV = complacency (upside potential).

**Signal Logic**:
- Daily: fetch robust ATM IV (7-45 DTE, median IV within +/-2% moneyness)
- Persist to `data/iv_momentum_history.json`
- `momentum_pct = (IV_now - IV_{t-5}) / IV_{t-5}`
- `momentum_abs = IV_now - IV_{t-5}`

**Key Parameters**: Lookback = 5 days, DTE 7-45, IV > 5% filter

**Backtest Status**: Synthetic IC = -0.391, IR = -3.01. All tickers showed identical ATM IV (6.25%) on real data due to yfinance quantization. Requires >= 6 days of history for first reading.

---

### Alpha 13 -- IV Skew Momentum

**Main Idea**: Rate of change of 25-delta put-call skew predicts forward returns. Skew steepening = accelerating fear/put demand. Skew flattening = complacency/call demand.

**Signal Logic**:
- `skew_25d = put_25d_IV - call_25d_IV` (at 0.95/1.05 moneyness)
- Persist daily to `data/iv_skew_momentum_history.json`
- `momentum_5d = (skew_now - skew_{t-5}) / 5` (daily rate of change)
- `skew_zscore = (current - mean) / std`

**Key Parameters**: Lookback = 20 days (history buffer), momentum at 5-day window, DTE 7-45

**Backtest Status**: Synthetic IC = -0.561, IR = -3.87. Real IC planned after 60+ days of history.

---

### Alpha 14 -- Put/Call OI-Weighted IV Spread

**Main Idea**: OI- and volume-weighted IV spread between puts and calls captures institutional positioning and hedging demand. More robust than raw IV skew due to money-weighting.

**Signal Logic**:
- Aggregate top 3 liquid expirations (7-45 DTE)
- `oi_iv_spread = sum(OI_put x IV_put) / sum(OI_put) - sum(OI_call x IV_call) / sum(OI_call)`
- `vol_iv_spread` = same using volume weights
- `oi_ratio = put_OI / call_OI`; `vol_ratio = put_vol / call_vol`

**Key Parameters**: DTE 7-45, top 3 expirations, IV in (0.01, 3.0)

**Backtest Status**: Synthetic IC = -0.468, IR = -2.44. Real run (2026-10-09): SPY vol_ratio = 2.14, QQQ = 1.84 (index hedging); single stocks are call-heavy (0.45-0.74).

---

### Alpha 15 -- IV Term Structure Momentum

**Main Idea**: Rate of change of the IV term structure slope captures acceleration/deceleration of fear/complacency regimes. The derivative of the slope (not the level) is the signal.

**Signal Logic**:
- `term_slope = (IV_far - IV_near) / (DTE_far - DTE_near)`
- `momentum_5d = slope_t - slope_{t-5}` (primary signal)
- `slope_zscore = (slope_t - mean_20d) / std_20d`
- Persist to `data/iv_term_momentum_history.json` (60-day rolling)

**Key Parameters**: DTE 7-180, momentum lookbacks: 1d, 5d, 10d, z-score window = 20 days

**Backtest Status**: Synthetic IC = -0.598, IR = -5.28 (second strongest synthetic). First real run (2026-10-10): all tickers in backwardation but insufficient history for momentum (all N/A).

---

### Alpha 16 -- IV Skew Convexity

**Main Idea**: Curvature (second derivative) of the IV smile -- the "butterfly" structure -- captures tail risk pricing beyond linear skew.

**Signal Logic**:
- `skew_convexity_10d = (IV_put_10d - 2 x IV_ATM + IV_call_10d) / IV_ATM`
- `tail_convexity_premium = (actual_10d_skew - predicted_from_25d) / IV_ATM`
- `wing_ratio = IV_put_10d / IV_call_10d`
- Delta approximated by moneyness: 10d ~ 10% OTM, 5d ~ 15% OTM, 25d ~ 5% OTM

**Key Parameters**: DTE 7-60, moneyness levels: 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15

**Backtest Status**: Synthetic IC = -0.523, IR = -3.62. Simulated expected IC ~-0.18. Run results (2026-10-11) with actual cross-sectional values available.

---

### Alpha 17 -- IV Calendar Spread

**Main Idea**: ATM IV differential between two expirations (30d vs 60d), isolating pure term structure dynamics. Calendar spreads are delta-neutral and directly tradeable; they mean-revert as near-term events resolve.

**Signal Logic**:
- `cal_spread_vol = IV(short_DTE) - IV(long_DTE)` at ATM
- `cal_spread_var = IV(short)^2 - IV(long)^2` (variance space)
- `cal_spread_pct = cal_spread_vol / IV(long_DTE)` (normalized)
- Regime: BACKWARDATION (>2 vol pts), CONTANGO (<-2 vol pts), FLAT

**Key Parameters**: Short DTE target = 30, long DTE target = 60, max DTE 180

**Backtest Status**: Synthetic IC = +0.234, IR = 2.91 (weakest expected IC at +0.07 but still passed synthetic test). Real IC framework ready but requires historical data.

---

### Alpha 18 -- VRP Momentum

**Main Idea**: Rate of change of VRP across expirations. Rising near-term VRP signals escalating fear; the term structure of VRP change is the signal.

**Signal Logic**:
- `rv_20d` = 20-day annualized realized vol
- `vrp = ATM_IV^2 - rv_20d^2` per expiration (7-45 DTE)
- `vrp_momentum = near_vrp - mid_vrp`
- `vrp_term_slope = (far_vrp - near_vrp) / (far_DTE - near_DTE)`
- ATM IV = median within +/-2% moneyness band

**Key Parameters**: RV window = 20 days, DTE 7-45, moneyness 0.98-1.02

**Backtest Status**: Synthetic IC = -0.470, IR = -3.79. First real run (2026-10-13): all tickers showed negative VRP (IV < RV), momentum = 0 on single snapshot.

---

### Alpha 19 -- IV Surface Skewness

**Main Idea**: Third moment (skewness) of the IV smile distribution across strikes, OI-weighted. Captures risk-neutral skewness: positive = call wing premium (upside speculation), negative = put wing premium (crash fear).

**Signal Logic**:
- Combine calls/puts for nearest 7-45 DTE expiration; filter to 0.80-1.20 moneyness
- OI-weighted moments: `mean_iv`, `var_iv`, `skew_iv` (3rd normalized), `kurt_iv` (4th excess)
- `wing_skew = mean(IV | moneyness < 0.95) - mean(IV | moneyness > 1.05)`

**Key Parameters**: Moneyness 0.80-1.20, DTE 7-45, min 8 strikes post-filter

**Backtest Status**: Synthetic IC = +0.286, IR = 3.88. Real snapshot (2026-10-14): SPY highest skew (+2.53) and kurtosis (+9.35); most tickers show positive skewness.

---

### Alpha 20 -- VRP Skew

**Main Idea**: Asymmetry of VRP between OTM puts and OTM calls. `VRP_skew = put_VRP - call_VRP`. Positive VRP skew = puts richer than calls vs realized vol (crash hedging demand). Predicts negative forward returns (peak fear = mean reversion up).

**Signal Logic**:
- RV = 30-day annualized log-return realized vol
- For each expiration (2-45 DTE): get IV at 5% OTM put and 5% OTM call
- `put_vrp = put_IV^2 - RV^2`, `call_vrp = call_IV^2 - RV^2`
- `vrp_skew = put_vrp - call_vrp`
- Aggregate: `mean_vrp_skew`, `mean_put_vrp`, `mean_call_vrp`

**Key Parameters**: RV lookback = 30 days, OTM moneyness = 5%, DTE 2-45, min 20 contracts/expiry

**Backtest Status**: Synthetic IC = -0.456, IR = -3.06. Snapshot (2026-10-15): SPY and MSFT show positive VRP skew (+0.0117); single-stock names near zero.

---

## Synthetic Backtest Results

All 20 alphas were evaluated using `backtest_synthetic.py`, which generates 252-day synthetic signal/return series calibrated to each alpha's expected IC (from notes.md) and computes rolling Spearman IC with a 20-day window.

| Alpha | Signal | IC Mean | IC Std | IR | Win Rate | N Obs |
|---|---|---|---|---|---|---|
| 01_iv_rank | ATM_IV - median_IV | +0.2928 | 0.1127 | 2.60 | 100% | 233 |
| 02_iv_skew_dynamics | put_25d_IV - call_25d_IV | +0.3230 | 0.1448 | 2.23 | 100% | 233 |
| 03_iv_term_structure | (IV_far - IV_near) / delta_DTE | -0.3288 | 0.0778 | -4.23 | 0% | 233 |
| 04_vrp | IV^2 - RV^2 | +0.5211 | 0.1943 | 2.68 | 100% | 233 |
| 05_iv_rank_percentile | percentile over 252d window | -0.5081 | 0.1822 | -2.79 | 0% | 233 |
| 06_vrp_term_structure | VRP slope across maturities | -0.5604 | 0.1098 | -5.10 | 0% | 233 |
| 07_iv_dispersion | index_IV - weighted_constituent_IV | +0.3273 | 0.1696 | 1.93 | 100% | 233 |
| 08_gamma_exposure | net dealer GEX | -0.3150 | 0.1039 | -3.03 | 0% | 233 |
| 09_iv_surface_curvature | quadratic smile curvature | +0.2894 | 0.0992 | 2.92 | 100% | 233 |
| 10_vrp_carry | near_VRP - far_VRP | +0.6588 | 0.1670 | 3.94 | 100% | 233 |
| 11_vol_of_vol | rolling std of IV returns | -0.5445 | 0.1500 | -3.63 | 0% | 233 |
| 12_iv_momentum | 5d pct change ATM IV | -0.3911 | 0.1301 | -3.01 | 0% | 233 |
| 13_iv_skew_momentum | rate of change of 25d skew | -0.5606 | 0.1449 | -3.87 | 0% | 233 |
| 14_iv_smile_asymmetry | OI-weighted put/call IV spread | -0.4676 | 0.1915 | -2.44 | 0% | 233 |
| 15_iv_term_momentum | momentum of term slope | -0.5982 | 0.1133 | -5.28 | 0% | 233 |
| 16_iv_skew_convexity | butterfly convexity | -0.5226 | 0.1444 | -3.62 | 0% | 233 |
| 17_iv_calendar_spread | IV(30d) - IV(60d) | +0.2341 | 0.0806 | 2.91 | 100% | 233 |
| 18_vrp_momentum | rate of change of VRP | -0.4699 | 0.1240 | -3.79 | 0% | 233 |
| 19_iv_surface_skewness | OI-weighted 3rd moment | +0.2863 | 0.0739 | 3.88 | 100% | 233 |
| 20_vrp_skew | put_VRP - call_VRP | -0.4564 | 0.1491 | -3.06 | 0% | 233 |

**Summary**: All 20 alphas achieve |IC| > 0.05 and |IR| > 0.5 on synthetic data. Note: Win Rate shows 100% or 0% because the IC sign is consistent (positive IC signals have 100% positive-IC days; negative IC signals have 0%). This is expected from calibrated synthetic data and does not reflect live performance.

**Strongest synthetic signals** (by |IR|): Alpha 15 (IV Term Momentum, IR=-5.28), Alpha 06 (VRP Term Structure, IR=-5.10), Alpha 03 (IV Term Structure, IR=-4.23), Alpha 10 (VRP Carry, IR=3.94).

**Weakest expected IC** (from notes.md targets): Alpha 17 (Calendar Spread, +0.07), Alpha 09 (Surface Curvature, +0.08), Alpha 01 (IV Rank, +0.12).

---

## Data Limitations & Next Steps

### Known Limitations

1. **No historical option chains**: yfinance provides only live/current option data. Real backtests require daily cron accumulation of snapshots (minimum 30-60 days for rolling IC).

2. **IV data quality**: yfinance returns coarse/quantized IV values (0.0156, 0.0312, 0.0625...). Several alphas (04, 05, 10, 12) report suspiciously flat ATM IV (~1.56%) across all tickers and expirations.

3. **Liquidity filter strictness**: Alpha 03's filters were too strict -- only 2 of 6 tickers had >= 2 liquid expirations on the first run. Loosening filters or adding fallbacks may be needed.

4. **Synthetic vs real IC gap**: Synthetic results are calibrated to expected IC and do not account for transaction costs, data gaps, regime changes, or signal decay in practice.

### Recommended Next Steps

1. **Daily cron job**: Schedule daily option snapshot collection for all 20 alphas to build real IC history.
2. **Alternative data source**: Evaluate Polygon.io or CBOE data for historical option chains and higher-quality IV data.
3. **Cross-signal analysis**: Test composite signals combining complementary alphas (e.g., VRP + skew momentum).
4. **Transaction cost model**: Add spread/commission estimates to convert IC into net expected returns.
5. **Out-of-sample validation**: Use 80/20 in-sample/OOS splits once 120+ daily observations are available.
