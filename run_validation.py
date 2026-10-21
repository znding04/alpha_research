#!/usr/bin/env python3
"""Run the pre-registered tradability validation for every alpha with a validation.py.

Each alpha_*/validation.py exposes NAME, a docstring with the pre-registered design,
and build(data) -> list[common.validation.Test]. Shared pass rule: common/validation.py.

Outputs:
    results/validation/<alpha>_{ic,perf,alpha}.csv   full grids, every test of that alpha
    results/VALIDATION.md                           scoreboard (primary test decides)
    figures/validation/<alpha>.png                  log cumulative net returns

Usage: python3 run_validation.py [alpha_07 ...] [--selftest]
    --selftest: sanity-check the pipeline (look-ahead signal must PASS, random signal must FAIL).
"""

import importlib
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
from common.validation import IS_END, OOS_START, run

OUT = os.path.join(ROOT, "results", "validation")
FIG = os.path.join(ROOT, "figures", "validation")


def discover(only):
    for d in sorted(os.listdir(ROOT)):
        if d.startswith("alpha_") and os.path.exists(os.path.join(ROOT, d, "validation.py")):
            if not only or any(d.startswith(o) for o in only):
                yield d, importlib.import_module(f"{d}.validation")


def plot(folder, results, path):
    fig, axes = plt.subplots(1, len(results), figsize=(6 * len(results), 3.8), squeeze=False)
    for ax, r in zip(axes[0], results):
        for k, c in r["curves"].items():
            c = c.dropna()
            ax.plot(np.log1p(c).cumsum(), lw=1.4 if k.startswith(r["alpha"]) else 0.8, label=k)
        ax.axvline(pd.Timestamp(OOS_START), color="k", ls="--", lw=0.8)
        ax.set_title(f"{r['instrument']}{'' if r['primary'] else ' (secondary)'}: log cum. net return", fontsize=9)
        ax.legend(fontsize=7)
    fig.suptitle(folder, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def selftest(data):
    from common import instruments as I
    from common.validation import Test, fwd_compound
    rng = np.random.default_rng(0)
    spy, vx = I.spy(data), I.vix_futures()
    panel = I.hedged_straddles(data)
    cases = {
        "peek SPY (must PASS)": (Test("peek", "timing", fwd_compound(spy.daily, 5), spy), True),
        "random SPY (must FAIL)": (Test("rand", "timing", pd.Series(rng.normal(size=len(spy.daily)), spy.daily.index), spy), False),
        "peek VIX futures (must PASS)": (Test("peek", "timing", fwd_compound(vx.daily, 5), vx), True),
        "noisy peek straddles (must PASS)": (Test("peek", "cross_section", panel.ret + rng.normal(
            scale=2 * float(np.nanstd(panel.ret.values)), size=panel.ret.shape), panel), True),
        "random straddles (must FAIL)": (Test("rand", "cross_section", pd.DataFrame(
            rng.normal(size=panel.ret.shape), panel.ret.index, panel.ret.columns), panel), False),
    }
    ok = True
    for k, (t, want) in cases.items():
        r = run(t)
        good = r["passed"] == want
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {k}: OOS IC {r['oos_ic']:+.3f}, alpha t {r['oos_alpha_t']:+.1f}")
    print("selftest", "passed" if ok else "FAILED")
    return ok


def main():
    only = [a for a in sys.argv[1:] if not a.startswith("-")]
    data = load_history()
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest(data) else 1)
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    board = []
    for folder, mod in discover(only):
        print(f"\n=== {folder} ===", flush=True)
        results = [run(t) for t in mod.build(data)]
        for kind in ("ic", "perf", "reg"):
            pd.concat([r[kind].assign(instrument=r["instrument"]) for r in results]).round(4).to_csv(
                os.path.join(OUT, f"{folder}_{'alpha' if kind == 'reg' else kind}.csv"), index=False)
        plot(folder, results, os.path.join(FIG, f"{folder}.png"))
        for r in results:
            print(f"  {r['instrument']}{'' if r['primary'] else ' (secondary)'}: "
                  f"OOS IC {r['oos_ic']:+.3f} (t {r['oos_ic_t']:+.1f}, IS {r['is_ic']:+.3f}) | "
                  f"OOS alpha {r['oos_alpha_ann']:+.1%}/yr (t {r['oos_alpha_t']:+.1f}) | "
                  f"OOS net {r['oos_ann_ret']:+.1%}/yr, Sharpe {r['oos_sharpe']:+.2f} | "
                  f"gross {r['oos_gross_ann']:+.1%}/yr, Sharpe {r['oos_gross_sharpe']:+.2f}, "
                  f"break-even cost {r['breakeven_cost']:.2%} vs assumed {r['assumed_cost']:.2%} → "
                  f"{'PASS' if r['passed'] else 'FAIL'}")
            board.append({"folder": folder, "name": mod.NAME, **{k: v for k, v in r.items()
                                                                  if k not in ("ic", "perf", "reg", "curves")}})
    if not only:
        write_board(pd.DataFrame(board))


def write_board(b):
    lines = [
        "# Tradability Validation",
        "",
        f"Pre-registered test per alpha (design in each `alpha_*/validation.py`, rule in `common/validation.py`). "
        f"In-sample ≤ {IS_END} (only the trade direction is chosen there), out-of-sample ≥ {OOS_START}, after costs, "
        "1-day execution lag. **Pass** = OOS IC with the in-sample sign and |t| ≥ 2, **and** positive OOS alpha "
        "(NW t ≥ 2) after regressing on every benchmark strategy. Only the primary test decides; secondary tests are context.",
        "",
        "| Alpha | Signal | Test | Instrument | IS IC | OOS IC (t) | OOS alpha /yr (t) | OOS net ret /yr (Sharpe) | OOS gross Sharpe | Break-even cost (assumed) | Verdict |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in b.iterrows():
        verdict = ("✅ PASS" if r.passed else "❌ FAIL") if r.primary else ("pass" if r.passed else "fail")
        lines.append(
            f"| {r.folder} | {r['name']} | {'primary' if r.primary else 'secondary'} | {r.instrument} | "
            f"{r.is_ic:+.3f} | {r.oos_ic:+.3f} ({r.oos_ic_t:+.1f}) | {r.oos_alpha_ann:+.1%} ({r.oos_alpha_t:+.1f}) | "
            f"{r.oos_ann_ret:+.1%} ({r.oos_sharpe:+.2f}) | {r.oos_gross_sharpe:+.2f} | "
            f"{r.breakeven_cost:.2%} ({r.assumed_cost:.2%}) | {verdict} |")
    lines += ["", "IC horizon: 5d forward return for timing tests, one 5-day period for cross-section tests. "
              "Break-even cost = OOS gross mean return / mean turnover: the cost per unit traded "
              "(fraction of notional; of straddle premium for the panel, round trip) at which the net return is zero. "
              "Grids: `results/validation/`. Charts: `figures/validation/`.", ""]
    open(os.path.join(ROOT, "results", "VALIDATION.md"), "w").write("\n".join(lines))
    print("\nWrote results/VALIDATION.md")


if __name__ == "__main__":
    main()
