#!/usr/bin/env python3
"""Run historical (time-series + cross-sectional) IC analysis for every alpha.

Each alpha_*/historical.py exposes:
    NAME           short signal name
    HYPOTHESIS     expected sign of IC vs forward returns (+1 / -1), from notes.md
    compute_signal(data: HistData) -> DataFrame (date x ticker)

Outputs:
    results/historical_ic.csv      every alpha x target x horizon x (cs | ts)
    results/HISTORICAL.md          headline table
    figures/historical/<alpha>.png cumulative IC

Usage: python3 run_historical.py [alpha_04 alpha_05 ...] [--refresh]
"""

import importlib.util
import os
import sys
import warnings

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common.history import load_history
from common.ic_engine import HORIZONS, evaluate

RESULTS_DIR = os.path.join(ROOT, "results")
FIG_DIR = os.path.join(ROOT, "figures", "historical")


def discover(only=None):
    mods = []
    for d in sorted(os.listdir(ROOT)):
        path = os.path.join(ROOT, d, "historical.py")
        if d.startswith("alpha_") and os.path.exists(path):
            if only and not any(d.startswith(o) for o in only):
                continue
            spec = importlib.util.spec_from_file_location(f"{d}.historical", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mods.append((d, mod))
    return mods


def flatten(alpha, res, hyp):
    rows = []
    for key, r in res.items():
        target, h = key.split("_")
        for kind in ("cs", "ts"):
            m = r[kind]
            if not m:
                continue
            rows.append({
                "alpha": alpha, "target": target, "horizon": int(h[:-1]), "kind": kind,
                "ic": m["ic"], "t": m["t"], "hit": m.get("hit", np.nan),
                "n": m.get("n", m.get("n_tickers")),
                "ic_pre2019": m.get("ic_pre2019", np.nan),
                "ic_post2019": m.get("ic_post2019", np.nan) if kind == "cs" else np.nanmean(
                    [v["ic_post2019"] for v in m["per_ticker"].values()]),
                "hypothesis": hyp,
            })
    return rows


def plot(alpha, res, path):
    fig, ax = plt.subplots(figsize=(8, 3.5))
    drew = False
    for h in HORIZONS:
        cs = res[f"ret_{h}d"]["cs"]
        if cs:
            ax.plot(cs["series"].cumsum() / h, label=f"cross-sectional, {h}d fwd return")
            drew = True
    if not drew:  # single-underlying signal: show per-ticker TS IC as bars instead
        per = res["ret_21d"]["ts"].get("per_ticker", {})
        ax.bar(list(per), [v["ic"] for v in per.values()])
        ax.set_ylabel("time-series IC (21d)")
    else:
        ax.set_ylabel("cumulative IC / h")
        ax.legend(fontsize=8)
    ax.axhline(0, color="grey", lw=0.5)
    ax.set_title(alpha)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def headline(df):
    """One row per alpha: 21d IC vs returns (cs if available, else ts) and vs IV change."""
    out = []
    for alpha, g in df.groupby("alpha"):
        def pick(target):
            sub = g[(g.target == target) & (g.horizon == 21)]
            row = sub[sub.kind == "cs"] if (sub.kind == "cs").any() else sub[sub.kind == "ts"]
            return row.iloc[0] if len(row) else None
        r, v = pick("ret"), pick("div")
        out.append({
            "alpha": alpha, "kind": r.kind, "hypothesis": int(r.hypothesis),
            "ic_ret_21d": r.ic, "t_ret_21d": r.t, "ic_post2019": r.ic_post2019,
            "ic_div_21d": v.ic if v is not None else np.nan, "t_div_21d": v.t if v is not None else np.nan,
        })
    return pd.DataFrame(out)


def verdict(r):
    agrees = np.sign(r.ic_ret_21d) == r.hypothesis
    stable = np.sign(r.ic_post2019) == np.sign(r.ic_ret_21d)
    if abs(r.t_ret_21d) >= 2 and agrees and stable:
        return "✅ significant, as hypothesized"
    if abs(r.t_ret_21d) >= 2 and not agrees:
        return "⚠️ significant, opposite sign"
    if abs(r.t_ret_21d) >= 2:
        return "⚠️ significant but unstable post-2019"
    return "❌ not significant"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    data = load_history(refresh="--refresh" in sys.argv)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)

    rows = []
    for alpha, mod in discover(args):
        sig = mod.compute_signal(data)
        res = evaluate(sig, data)
        rows += flatten(alpha, res, mod.HYPOTHESIS)
        plot(alpha, res, os.path.join(FIG_DIR, f"{alpha}.png"))
        span = sig.dropna(how="all").index
        print(f"✅ {alpha} ({mod.NAME}): {sig.shape[1]} tickers, {span.min().date()} → {span.max().date()}")

    df = pd.DataFrame(rows)
    csv_path = os.path.join(RESULTS_DIR, "historical_ic.csv")
    if args and os.path.exists(csv_path):  # partial run: merge with previous results
        old = pd.read_csv(csv_path)
        df = pd.concat([old[~old.alpha.isin(df.alpha)], df]).sort_values(["alpha", "target", "horizon", "kind"])
    df.round(4).to_csv(csv_path, index=False)

    hl = headline(df)
    hl["verdict"] = hl.apply(verdict, axis=1)
    lines = [
        "# Historical IC Summary",
        "",
        f"Data: CBOE implied-vol indices + yfinance prices, through {data.prices.index.max().date()}. "
        "Signal at close t, forward window starts at close t+1. "
        "`cs` = daily cross-sectional rank IC across the ETF/single-name universe (NW t-stat); "
        "`ts` = time-series rank IC per underlying, averaged (t ≈ IC·√(N/h)). "
        "Hypothesis = expected IC sign vs forward returns from each alpha's notes.md.",
        "",
        "| Alpha | Kind | Hyp. | IC (21d ret) | t | IC post-2019 | IC (21d ΔIV) | t | Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in hl.iterrows():
        lines.append(
            f"| {r.alpha} | {r.kind} | {'+' if r.hypothesis > 0 else '−'} | {r.ic_ret_21d:+.3f} | {r.t_ret_21d:+.1f} | "
            f"{r.ic_post2019:+.3f} | {r.ic_div_21d:+.3f} | {r.t_div_21d:+.1f} | {r.verdict} |")
    lines += ["", "Full grid (1/5/21d, both targets, cs and ts): `results/historical_ic.csv`. "
              "Charts: `figures/historical/`."]
    with open(os.path.join(RESULTS_DIR, "HISTORICAL.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines[4:]))


if __name__ == "__main__":
    main()
