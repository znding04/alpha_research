"""Pre-registered tradability validation, shared by every alpha_*/validation.py.

An IC alone does not make an alpha. A signal passes only if, out of sample and
after costs, it predicts a TRADABLE instrument's returns AND earns returns that
known, simpler strategies on the same instrument do not already explain.

Two test types:

timing (one instrument, e.g. SPY or 30d VIX futures)
    w_t = s * (2 * pct_t - 1), pct_t = percentile of the signal in its trailing 252 days
    (data <= t only). Decided at close t, held from close t+1 (1-day lag), daily rebalance.
    s = sign of the in-sample IC vs the 5d forward return: the only thing fit in-sample.

cross_section (a panel, e.g. delta-hedged straddles on the 17-name universe)
    Every `step` trading days: rank the signal across names, w = s * (rank centred,
    sum |w| = 1), hold one non-overlapping period. s = sign of the in-sample mean cs IC.

Pass rule, both types (OOS = from OOS_START on):
    (i)  OOS IC vs forward returns (the instrument's, at the primary horizon) has the
         in-sample sign and |t| >= 2;
    (ii) the strategy's OOS net returns have a positive regression intercept with
         Newey-West t >= 2, controlling for every benchmark strategy.
Anything less = NOT a tradable alpha. Secondary instruments are reported, never scored.

Each alpha_*/validation.py exposes NAME, DESIGN (the pre-registration text) and
build(data) -> list[Test]; run_validation.py runs them.
"""

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from common.ic_engine import nw_tstat

IS_END = "2018-12-31"
OOS_START = "2019-01-01"
HORIZONS = (1, 5, 21)
SIGN_HORIZON = 5
PCT_WINDOW = 252
T_PASS = 2.0


# ----------------------------------------------------------------------------- data classes

@dataclass
class Instrument:
    """Daily return series where daily[d] = return from close d to the next close."""
    name: str
    daily: pd.Series
    cost_fn: Callable[[pd.Series], pd.Series]  # turnover (|Δw|) -> cost as a return
    borrow: float = 0.0                         # annual cost on short exposure
    static: dict = field(default_factory=dict)  # benchmark name -> constant weight, e.g. {"always short": -1}


@dataclass
class Panel:
    """Non-overlapping period returns per name: ret.loc[t] = return of a position decided at close t."""
    name: str
    ret: pd.DataFrame
    step: int
    cost: float  # cost per unit of gross exposure traded, as a return (round trip per period)


@dataclass
class Test:
    alpha: str
    kind: str                      # "timing" | "cross_section"
    signal: pd.Series | pd.DataFrame
    instrument: Instrument | Panel
    controls: dict = field(default_factory=dict)  # name -> control signal, same construction & own IS sign
    primary: bool = True


# ----------------------------------------------------------------------------- building blocks

def fwd_compound(daily: pd.Series, h: int) -> pd.Series:
    """Compounded return of daily[t+1..t+h], aligned to t (position decided at t opens at close t+1)."""
    logr = np.log1p(daily)
    return np.expm1(logr[::-1].rolling(h).sum()[::-1].shift(-1))


def ts_ic(sig, tgt, h):
    df = pd.concat([sig, tgt], axis=1).dropna()
    if len(df) < 100:
        return np.nan, np.nan, 0
    ic = df.iloc[:, 0].rank().corr(df.iloc[:, 1].rank())
    return ic, ic * np.sqrt(len(df) / h), len(df)


def rolling_pct(x: pd.Series, n=PCT_WINDOW) -> pd.Series:
    return x.rolling(n, min_periods=int(n * 0.8)).apply(lambda a: (a <= a[-1]).mean(), raw=True)


def timing_returns(sig: pd.Series, inst: Instrument, s: float, gross: bool = False):
    """Net daily P&L of w_t = s·(2·pct−1) decided at t, earning daily[t+1].

    gross=True returns (gross P&L, turnover) with no costs, for the break-even cost.
    """
    w = (s * (2 * rolling_pct(sig) - 1)).reindex(inst.daily.index)
    w_held = w.shift(1)
    pnl = w_held * inst.daily
    turnover = w_held.diff().abs()
    if gross:
        return pnl.dropna(), turnover.reindex(pnl.dropna().index)
    net = pnl - inst.cost_fn(turnover) - inst.borrow / 252 * w_held.clip(upper=0).abs()
    return net.dropna()


def static_returns(inst: Instrument, w: float) -> pd.Series:
    """Constant-weight benchmark (no turnover after entry)."""
    return w * inst.daily - inst.borrow / 252 * max(-w, 0)


def cs_weights(sig: pd.DataFrame) -> pd.DataFrame:
    r = sig.rank(axis=1)
    r = r.sub(r.mean(axis=1), axis=0)
    return r.div(r.abs().sum(axis=1), axis=0)


def cs_ic(sig: pd.DataFrame, ret: pd.DataFrame, min_names=8) -> pd.Series:
    sig, ret = sig.reindex_like(ret), ret
    m = sig.notna() & ret.notna()
    rs, rr = sig.where(m).rank(axis=1), ret.where(m).rank(axis=1)
    ic = rs.sub(rs.mean(axis=1), axis=0).mul(rr.sub(rr.mean(axis=1), axis=0)).sum(axis=1)
    den = np.sqrt((rs.sub(rs.mean(axis=1), axis=0) ** 2).sum(axis=1) * (rr.sub(rr.mean(axis=1), axis=0) ** 2).sum(axis=1))
    return (ic / den.replace(0, np.nan)).where(m.sum(axis=1) >= min_names).dropna()


def panel_returns(sig: pd.DataFrame, panel: Panel, s: float, gross: bool = False):
    """Net period return of the rank-weighted long/short book (positions fully turned over each period).

    gross=True returns (gross return, gross exposure traded) with no costs, for the break-even cost.
    """
    sig = sig.reindex(panel.ret.index).where(panel.ret.notna())
    w = s * cs_weights(sig)
    pnl = (w * panel.ret).sum(axis=1, min_count=1).dropna()
    traded = w.abs().sum(axis=1).reindex(pnl.index)
    return (pnl, traded) if gross else pnl - panel.cost * traded


def perf(r: pd.Series, periods_per_year=252) -> dict:
    r = r.dropna()
    if len(r) < 30:
        return {}
    eq = (1 + r).cumprod()
    return {
        "ann_ret": (1 + r).prod() ** (periods_per_year / len(r)) - 1,
        "ann_vol": r.std() * np.sqrt(periods_per_year),
        "sharpe": r.mean() / r.std() * np.sqrt(periods_per_year) if r.std() > 0 else np.nan,
        "max_dd": (eq / eq.cummax() - 1).min(),
        "n": len(r),
    }


def alpha_regression(y: pd.Series, X: pd.DataFrame, periods_per_year=252, lags=5) -> dict:
    """OLS of y on X with intercept; Newey-West t for the intercept."""
    df = pd.concat([y.rename("y"), X], axis=1).dropna()
    A = np.column_stack([np.ones(len(df)), df[X.columns].values])
    beta, *_ = np.linalg.lstsq(A, df["y"].values, rcond=None)
    resid = df["y"].values - A @ beta
    XtX_inv = np.linalg.inv(A.T @ A)
    u = A * resid[:, None]
    S = u.T @ u
    for k in range(1, lags + 1):
        G = u[k:].T @ u[:-k]
        S += (1 - k / (lags + 1)) * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    return {"alpha_ann": beta[0] * periods_per_year, "alpha_t": beta[0] / np.sqrt(V[0, 0]),
            **{f"beta[{c}]": b for c, b in zip(X.columns, beta[1:])}, "n": len(df)}


def _periods(index):
    return {"IS": index <= pd.Timestamp(IS_END), "OOS": index >= pd.Timestamp(OOS_START)}


# ----------------------------------------------------------------------------- runners

def run_timing(test: Test) -> dict:
    inst = test.instrument
    sigs = {test.alpha: test.signal, **test.controls}
    ic_rows, perf_rows, strat = [], [], {}
    for sname, sig in sigs.items():
        sig = sig.reindex(inst.daily.index)
        for h in HORIZONS:
            tgt = fwd_compound(inst.daily, h)
            for p, m in _periods(sig.index).items():
                ic, t, n = ts_ic(sig[m], tgt[m], h)
                ic_rows.append({"signal": sname, "h": h, "period": p, "ic": ic, "t": t, "n": n})
        is_ic = ts_ic(sig.loc[:IS_END], fwd_compound(inst.daily, SIGN_HORIZON).loc[:IS_END], SIGN_HORIZON)[0]
        s = float(np.sign(is_ic)) if pd.notna(is_ic) and is_ic != 0 else 1.0
        strat[f"{sname} timing"] = (timing_returns(sig, inst, s), s)
        if sname == test.alpha:
            gross = timing_returns(sig, inst, s, gross=True)
    bench = {k: static_returns(inst, w) for k, w in inst.static.items()}
    curves = {k: r for k, (r, _) in strat.items()} | bench
    for k, r in curves.items():
        s = strat.get(k, (None, None))[1]
        for p, m in _periods(r.index).items():
            perf_rows.append({"strategy": k + (f" (s={int(s):+d})" if s else ""), "period": p, **perf(r[m])})
    y = curves[f"{test.alpha} timing"]
    X = pd.DataFrame({k: v for k, v in curves.items() if k != f"{test.alpha} timing"})
    reg = _regressions(y, X, 252)
    return _verdict(test, pd.DataFrame(ic_rows), pd.DataFrame(perf_rows), reg, curves, SIGN_HORIZON, gross, 252)


def run_cross_section(test: Test) -> dict:
    panel = test.instrument
    per_year = 252 / panel.step
    sigs = {test.alpha: test.signal, **test.controls}
    ic_rows, perf_rows, curves, signs = [], [], {}, {}
    for sname, sig in sigs.items():
        ic = cs_ic(sig, panel.ret)
        for p, m in _periods(ic.index).items():
            x = ic[m]
            ic_rows.append({"signal": sname, "h": panel.step, "period": p, "ic": x.mean(),
                            "t": nw_tstat(x, 2), "n": len(x)})
        s = float(np.sign(ic.loc[:IS_END].mean())) or 1.0
        signs[f"{sname} long/short"] = s
        curves[f"{sname} long/short"] = panel_returns(sig, panel, s)
        if sname == test.alpha:
            gross = panel_returns(sig, panel, s, gross=True)
    ew_short = -panel.ret.mean(axis=1) - panel.cost
    curves["equal-weight short (benchmark)"] = ew_short
    for k, r in curves.items():
        s = signs.get(k)
        for p, m in _periods(r.index).items():
            perf_rows.append({"strategy": k + (f" (s={int(s):+d})" if s else ""), "period": p,
                              **perf(r[m], per_year)})
    y = curves[f"{test.alpha} long/short"]
    X = pd.DataFrame({k: v for k, v in curves.items() if k != f"{test.alpha} long/short"})
    reg = _regressions(y, X, per_year)
    return _verdict(test, pd.DataFrame(ic_rows), pd.DataFrame(perf_rows), reg, curves, panel.step, gross, per_year)


def _regressions(y, X, per_year):
    rows = []
    for p, m in _periods(y.index).items():
        if p != "OOS":
            continue
        yy = y[m]
        for c in X.columns:
            rows.append({"period": p, "controls": c, **alpha_regression(yy, X[[c]], per_year)})
        rows.append({"period": p, "controls": "ALL benchmarks", **alpha_regression(yy, X, per_year)})
    rows.append({"period": "full", "controls": "ALL benchmarks", **alpha_regression(y, X, per_year)})
    return pd.DataFrame(rows)


def _assumed_cost(inst):
    if isinstance(inst, Panel):
        return inst.cost
    one = pd.Series(1.0, index=inst.daily.index)
    return float(inst.cost_fn(one).loc[OOS_START:].mean())


def _verdict(test, ic_df, perf_df, reg_df, curves, h, gross, per_year):
    me = ic_df[(ic_df.signal == test.alpha) & (ic_df.h == h)]
    is_ic = me[me.period == "IS"].ic.iloc[0]
    o = me[me.period == "OOS"].iloc[0]
    crit1 = bool(np.sign(o.ic) == np.sign(is_ic) and abs(o.t) >= T_PASS)
    r = reg_df[(reg_df.period == "OOS") & (reg_df.controls == "ALL benchmarks")].iloc[0]
    crit2 = bool(r.alpha_ann > 0 and r.alpha_t >= T_PASS)
    oos_perf = perf_df[(perf_df.period == "OOS") & perf_df.strategy.str.startswith(test.alpha)].iloc[0]
    g, traded = (x[x.index >= pd.Timestamp(OOS_START)] for x in gross)
    return {
        "oos_gross_ann": g.mean() * per_year,
        "oos_gross_sharpe": g.mean() / g.std() * np.sqrt(per_year),
        # cost per unit traded (as a return) at which the OOS net mean is zero
        "breakeven_cost": g.mean() / traded.mean() if traded.mean() > 0 else np.nan,
        "assumed_cost": _assumed_cost(test.instrument),
        "alpha": test.alpha, "kind": test.kind, "instrument": test.instrument.name, "primary": test.primary,
        "is_ic": is_ic, "oos_ic": o.ic, "oos_ic_t": o.t, "ic_h": h, "crit_ic": crit1,
        "oos_alpha_ann": r.alpha_ann, "oos_alpha_t": r.alpha_t, "crit_alpha": crit2,
        "oos_ann_ret": oos_perf.get("ann_ret"), "oos_sharpe": oos_perf.get("sharpe"),
        "passed": crit1 and crit2,
        "ic": ic_df, "perf": perf_df, "reg": reg_df, "curves": curves,
    }


def run(test: Test) -> dict:
    return run_timing(test) if test.kind == "timing" else run_cross_section(test)
