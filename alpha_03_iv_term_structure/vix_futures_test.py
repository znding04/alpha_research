#!/usr/bin/env python3
"""Rigorous tradability test of alpha_03 on VIX futures.

PRE-REGISTERED DESIGN (fixed before any futures results were computed, 2026-10-18)
---------------------------------------------------------------------------------
Signal      : alpha_03 term ratio = VIX3M / VIX − 1 at close t. Unchanged, no tuning.
Instruments : (a) 30-day constant-maturity long VIX futures (CBOE VX settlements,
                  common/vix_futures.py); (b) VIXY ETF (tradable, fees included).
Timing      : signal at close t, position held from close t+1 (1-day lag, as in all IC tests).
Split       : in-sample (IS) 2009-09 → 2018-12, out-of-sample (OOS) 2019-01 → today.
              Only the strategy DIRECTION is chosen in-sample: s = sign(IS IC vs 5d fwd CM return).
Strategy    : w_t = s × (2·pct_t − 1), pct_t = percentile of today's signal within the trailing
              252 days (uses data ≤ t only). Daily rebalance. Position ∈ [−1, +1].
Costs       : futures: half-spread 0.025 vol pts per unit traded (≈ 0.12–0.15% of price);
              VIXY: 5 bp per unit traded + 3%/yr borrow on short exposure.
Benchmarks  : (1) always short (w = −1) — the unconditional roll-yield trade;
              (2) VIX-level timing, (3) futures-basis timing (CM futures / VIX − 1, the
              known predictor of VIX futures returns) — same construction, own IS sign.
Pass rule   : alpha_03 is a VALID alpha only if, OOS and after costs,
              (i) IC vs 5d fwd CM return has the IS sign and |t| ≥ 2, AND
              (ii) the strategy's daily returns have a positive regression intercept with
                   NW |t| ≥ 2 after controlling for always-short AND basis-timing returns.
              Anything less = not a standalone tradable alpha.

Caveat: post-2019 *spot-return* ICs of this signal were already looked at, so the OOS
window is not fully untouched; the futures target, strategy and controls were not.
"""

import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yfinance as yf

from common.history import load_history
from common.ic_engine import nw_tstat
from common.vix_futures import constant_maturity_returns, load_vx_contracts

IS_END = "2018-12-31"
OOS_START = "2019-01-01"
HORIZONS = (1, 5, 21)
FUT_HALF_SPREAD = 0.025  # vol points
VIXY_COST = 0.0005
VIXY_BORROW = 0.03
OUT_DIR = os.path.join(ROOT, "results")
FIG = os.path.join(ROOT, "figures", "historical", "alpha_03_vix_futures.png")


def fwd_compound(daily: pd.Series, h: int) -> pd.Series:
    """Compounded return over the h days starting the day AFTER t (1-day lag).

    daily[d] = return from close d to the next close. Position decided at t opens at close t+1,
    so it earns daily[t+1], ..., daily[t+h].
    """
    logr = np.log1p(daily)
    return np.expm1(logr[::-1].rolling(h).sum()[::-1].shift(-1))


def ts_ic(sig, tgt, h):
    df = pd.concat([sig, tgt], axis=1).dropna()
    if len(df) < 100:
        return np.nan, np.nan, 0
    ic = df.iloc[:, 0].rank().corr(df.iloc[:, 1].rank())
    return ic, ic * np.sqrt(len(df) / h), len(df)


def rolling_pct(x: pd.Series, n=252) -> pd.Series:
    return x.rolling(n, min_periods=200).apply(lambda a: (a <= a[-1]).mean(), raw=True)


def strategy(sig, daily, s, cost_fn, borrow=0.0):
    """Daily P&L of w_t = s·(2·pct−1), entered at close t+1, earning daily[t+1]."""
    w = (s * (2 * rolling_pct(sig) - 1)).reindex(daily.index)
    w_held = w.shift(1)  # decided at t, held over day t+1 → t+2 (daily[t+1])
    gross = w_held * daily
    turnover = w_held.diff().abs()
    net = gross - cost_fn(turnover) - borrow / 252 * w_held.clip(upper=0).abs()
    return net.dropna(), w_held


def perf(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 50:
        return {}
    eq = (1 + r).cumprod()
    return {
        "ann_ret": (1 + r).prod() ** (252 / len(r)) - 1,
        "ann_vol": r.std() * np.sqrt(252),
        "sharpe": r.mean() / r.std() * np.sqrt(252) if r.std() > 0 else np.nan,
        "max_dd": (eq / eq.cummax() - 1).min(),
        "n": len(r),
    }


def alpha_regression(y: pd.Series, X: pd.DataFrame, lags=5):
    """OLS of y on X with intercept; NW t for the intercept."""
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    A = np.column_stack([np.ones(len(df)), df[X.columns].values])
    beta, *_ = np.linalg.lstsq(A, df["y"].values, rcond=None)
    resid = df["y"].values - A @ beta
    # NW variance of intercept via the residual-adjusted mean: regress-out approach
    XtX_inv = np.linalg.inv(A.T @ A)
    u = A * resid[:, None]
    S = u.T @ u
    for k in range(1, lags + 1):
        wk = 1 - k / (lags + 1)
        G = u[k:].T @ u[:-k]
        S += wk * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return {"alpha_ann": beta[0] * 252, "alpha_t": beta[0] / np.sqrt(V[0, 0]),
            **{f"beta_{c}": b for c, b in zip(X.columns, beta[1:])}, "n": len(df)}


def main():
    d = load_history()
    vix = d.spx_term["VIX"]
    signals = {
        "term_ratio (alpha_03)": (d.spx_term["VIX3M"] / vix - 1),
        "vix_level": vix,
    }
    cm = constant_maturity_returns(load_vx_contracts(2009))
    signals["futures_basis"] = (cm["cm_price"] / (vix * 100) - 1).reindex(vix.index)

    vixy = yf.download("VIXY", start="2011-01-01", auto_adjust=True, progress=False)["Close"].squeeze()
    vixy.index = pd.to_datetime(vixy.index).tz_localize(None)
    instruments = {
        "CM futures": (cm["cm_ret"], lambda to, p=cm["cm_price"]: to * FUT_HALF_SPREAD / p.reindex(to.index), 0.0),
        "VIXY": (vixy.pct_change().shift(-1).dropna(), lambda to: to * VIXY_COST, VIXY_BORROW),
    }

    ic_rows, perf_rows, reg_rows = [], [], []
    curves = {}
    for iname, (daily, cost_fn, borrow) in instruments.items():
        for sname, sig in signals.items():
            sig = sig.reindex(daily.index)
            for h in HORIZONS:
                tgt = fwd_compound(daily, h)
                for period, sl in [("IS", slice(None, IS_END)), ("OOS", slice(OOS_START, None))]:
                    ic, t, n = ts_ic(sig.loc[sl], tgt.loc[sl], h)
                    ic_rows.append({"instrument": iname, "signal": sname, "h": h, "period": period,
                                    "ic": ic, "t": t, "n": n})
        # direction chosen in-sample from 5d IC
        strat = {}
        for sname, sig in signals.items():
            sig = sig.reindex(daily.index)
            is_ic, _, _ = ts_ic(sig.loc[:IS_END], fwd_compound(daily, 5).loc[:IS_END], 5)
            s = np.sign(is_ic) if pd.notna(is_ic) else 1.0
            r, _ = strategy(sig, daily, s, cost_fn, borrow)
            strat[sname] = r
            for period, sl in [("IS", slice(None, IS_END)), ("OOS", slice(OOS_START, None))]:
                perf_rows.append({"instrument": iname, "strategy": f"{sname} timing (s={int(s):+d})",
                                  "period": period, **perf(r.loc[sl])})
        short = (-daily - cost_fn(pd.Series(0.0, index=daily.index)) - borrow / 252).rename("always_short")
        for period, sl in [("IS", slice(None, IS_END)), ("OOS", slice(OOS_START, None))]:
            perf_rows.append({"instrument": iname, "strategy": "always short (benchmark)", "period": period,
                              **perf(short.loc[sl])})
        # alpha of alpha_03 timing vs benchmarks, OOS and full
        X = pd.concat([short, strat["futures_basis"].rename("basis_timing")], axis=1)
        for period, sl in [("OOS", slice(OOS_START, None)), ("full", slice(None, None))]:
            y = strat["term_ratio (alpha_03)"].loc[sl]
            reg_rows.append({"instrument": iname, "period": period, "controls": "always short",
                             **alpha_regression(y, X[["always_short"]].loc[sl])})
            reg_rows.append({"instrument": iname, "period": period, "controls": "always short + basis timing",
                             **alpha_regression(y, X.loc[sl])})
            reg_rows.append({"instrument": iname, "period": period, "controls": "always short + VIX timing",
                             **alpha_regression(y, pd.concat([short, strat["vix_level"].rename("vix_timing")], axis=1).loc[sl])})
        curves[iname] = {**strat, "always short (benchmark)": short}

    ic_df, perf_df, reg_df = pd.DataFrame(ic_rows), pd.DataFrame(perf_rows), pd.DataFrame(reg_rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    ic_df.round(4).to_csv(os.path.join(OUT_DIR, "alpha_03_vixfut_ic.csv"), index=False)
    perf_df.round(4).to_csv(os.path.join(OUT_DIR, "alpha_03_vixfut_perf.csv"), index=False)
    reg_df.round(4).to_csv(os.path.join(OUT_DIR, "alpha_03_vixfut_alpha.csv"), index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    for ax, (iname, cs) in zip(axes, curves.items()):
        for k, r in cs.items():
            r = r.loc["2010-01-01":]
            ax.plot(np.log((1 + r.fillna(0)).cumprod()), label=k, lw=1)
        ax.axvline(pd.Timestamp(OOS_START), color="k", ls="--", lw=0.8)
        ax.set_title(f"{iname}: log cumulative return, after costs")
        ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG, dpi=110)

    pd.set_option("display.width", 220)
    piv = ic_df.pivot_table(index=["instrument", "signal", "h"], columns="period", values=["ic", "t"]).round(3)
    print("\nIC vs forward VIX-futures returns\n", piv.to_string())
    print("\nStrategy performance (after costs)\n", perf_df.round(3).to_string(index=False))
    print("\nalpha_03 timing: alpha vs benchmarks (NW t)\n", reg_df.round(3).to_string(index=False))

    # pass/fail
    oos5 = ic_df[(ic_df.instrument == "CM futures") & (ic_df.signal.str.startswith("term")) & (ic_df.h == 5)]
    is_sign = np.sign(oos5[oos5.period == "IS"].ic.iloc[0])
    o = oos5[oos5.period == "OOS"].iloc[0]
    crit1 = np.sign(o.ic) == is_sign and abs(o.t) >= 2
    r2 = reg_df[(reg_df.instrument == "CM futures") & (reg_df.period == "OOS") &
                (reg_df.controls == "always short + basis timing")].iloc[0]
    crit2 = r2.alpha_ann > 0 and abs(r2.alpha_t) >= 2
    print(f"\nPASS RULE: (i) OOS 5d IC {o.ic:+.3f} (t {o.t:+.1f}), IS sign {int(is_sign):+d} → {'PASS' if crit1 else 'FAIL'}; "
          f"(ii) OOS alpha vs short+basis {r2.alpha_ann:+.1%}/yr (t {r2.alpha_t:+.1f}) → {'PASS' if crit2 else 'FAIL'}")
    print(f"VERDICT: {'VALID tradable alpha' if crit1 and crit2 else 'NOT a standalone tradable alpha'}")


if __name__ == "__main__":
    main()
