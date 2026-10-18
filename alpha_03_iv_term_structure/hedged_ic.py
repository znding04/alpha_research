#!/usr/bin/env python3
"""Delta-hedged IC for alpha_03 (SPX IV term ratio = VIX3M/VIX − 1).

Question: does the term-structure signal predict *volatility* P&L once price
exposure is hedged away, not just the underlying's return?

Targets (see common/hedged.py):
- varswap_21d : RV²(next 21d) − VIX²   (model-free variance-swap P&L, hold to expiry)
- varswap_ret_21d : RV²/VIX² − 1        (same, per unit of variance notional; scale-free)
- straddle_hd : daily delta-hedged 30d ATM straddle return over h = 1, 5, 21 days

Underlyings: SPY (IV curve from VIX9D/VIX/VIX3M/VIX6M); QQQ, IWM, DIA as robustness
(flat IV from VXN/RVX/VXD — no term structure published for those).

Controls: the term ratio is correlated with the VIX level (backwardation happens
when VIX is high), so the same targets are also scored against the VIX level and
against the term ratio rank-residualized on the VIX level.

Run from repo root: python3 alpha_03_iv_term_structure/hedged_ic.py
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

from common.hedged import hedged_straddle_returns, spx_iv_at, variance_swap_pnl
from common.history import load_history
from common.ic_engine import SPLIT_DATE

HORIZONS = (1, 5, 21)
TICKERS = ["SPY", "QQQ", "IWM", "DIA"]
OUT_CSV = os.path.join(ROOT, "results", "alpha_03_hedged_ic.csv")
OUT_FIG = os.path.join(ROOT, "figures", "historical", "alpha_03_hedged_quintiles.png")


def ts_ic(sig, tgt, h):
    df = pd.concat([sig, tgt], axis=1).dropna()
    ic = df.iloc[:, 0].rank().corr(df.iloc[:, 1].rank())
    post = df[df.index >= SPLIT_DATE]
    ic_post = post.iloc[:, 0].rank().corr(post.iloc[:, 1].rank())
    return ic, ic * np.sqrt(len(df) / h), ic_post, len(df)


def rank_residual(x, control):
    """Residual of rank(x) on rank(control): the part of x not explained by control."""
    df = pd.concat([x, control], axis=1).dropna()
    rx, rc = df.iloc[:, 0].rank(pct=True), df.iloc[:, 1].rank(pct=True)
    beta = np.cov(rx, rc)[0, 1] / rc.var()
    return (rx - beta * rc).rename(x.name)


def main():
    d = load_history()
    term = d.spx_term.dropna(subset=["VIX9D", "VIX"])
    ratio = (d.spx_term["VIX3M"] / d.spx_term["VIX"] - 1).rename("term_ratio")
    vix = d.spx_term["VIX"].rename("vix_level")
    signals = {
        "term_ratio": ratio,
        "vix_level (control)": vix,
        "term_ratio | vix (residual)": rank_residual(ratio, vix),
    }

    def iv_fn_for(t):
        if t == "SPY":
            return lambda dt, m: spx_iv_at(term, m, dt) if dt in term.index else np.full(len(m), np.nan)
        flat = d.iv[t]
        return lambda dt, m: np.full(len(m), flat.get(dt, np.nan))

    targets = {}
    for t in TICKERS:
        vs = variance_swap_pnl(d.prices[t], d.iv[t], 21)
        targets[(t, "varswap_21d", 21)] = vs
        targets[(t, "varswap_ret_21d", 21)] = vs / d.iv[t].shift(-1) ** 2  # RV²/IV² − 1, scale-free
        for h in HORIZONS:
            print(f"  simulating {t} hedged straddle {h}d ...", flush=True)
            targets[(t, f"straddle_{h}d", h)] = hedged_straddle_returns(d.prices[t], iv_fn_for(t), h)
        targets[(t, "return_21d", 21)] = np.log(d.prices[t].shift(-22) / d.prices[t].shift(-1))

    rows = []
    for (t, tname, h), tgt in targets.items():
        for sname, sig in signals.items():
            if t != "SPY" and sname != "term_ratio":
                continue
            ic, tstat, ic_post, n = ts_ic(sig, tgt, h)
            rows.append({"ticker": t, "target": tname, "signal": sname, "ic": ic, "t": tstat,
                         "ic_post2019": ic_post, "n": n, "target_mean": tgt.mean()})
    res = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    res.round(4).to_csv(OUT_CSV, index=False)

    # Quintiles of the signal vs mean hedged straddle return (SPY, 21d)
    q = pd.concat([ratio, targets[("SPY", "straddle_21d", 21)].rename("straddle_21d"),
                   targets[("SPY", "varswap_ret_21d", 21)].rename("varswap_ret_21d"),
                   targets[("SPY", "return_21d", 21)].rename("return_21d")], axis=1).dropna()
    q["quintile"] = pd.qcut(q["term_ratio"], 5, labels=["Q1 backwardation", "Q2", "Q3", "Q4", "Q5 steep contango"])
    quint = q.groupby("quintile", observed=True).agg(
        term_ratio=("term_ratio", "mean"), straddle_21d=("straddle_21d", "mean"),
        straddle_hit=("straddle_21d", lambda x: (x > 0).mean()),
        varswap_ret_21d=("varswap_ret_21d", "mean"), return_21d=("return_21d", "mean"), n=("term_ratio", "size"))
    quint.round(4).to_csv(OUT_CSV.replace(".csv", "_quintiles.csv"))

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
    quint["straddle_21d"].plot.bar(ax=axes[0], color="tab:blue")
    axes[0].set_title("SPY delta-hedged 30d straddle, 21d return")
    quint["return_21d"].plot.bar(ax=axes[1], color="tab:green")
    axes[1].set_title("SPY 21d return (unhedged)")
    for ax in axes:
        ax.axhline(0, color="grey", lw=0.5)
        ax.set_xlabel("VIX3M/VIX quintile")
        ax.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=110)

    pd.set_option("display.width", 200)
    print("\n" + res.round(3).to_string(index=False))
    print("\n" + quint.round(4).to_string())
    print(f"\nSaved {OUT_CSV}, quintiles, and {OUT_FIG}")


if __name__ == "__main__":
    main()
