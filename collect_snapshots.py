#!/usr/bin/env python3
"""Daily snapshot collector: the only source of real option-chain history.

Runs every alpha_*/main.py, then archives the data/*_latest.csv files written
during this run into data/snapshots/<session>/, where <session> is the last
*completed* US trading session (a weekend or pre-close run maps to the prior
session). Snapshots are versioned in git so history survives machine changes.

Usage: python3 collect_snapshots.py [--force]
    --force   overwrite an existing snapshot folder for the session
"""

import glob
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
SNAP_DIR = os.path.join(DATA_DIR, "snapshots")
SESSION_CLOSE = (16, 15)  # ET; option settlement/quotes stable after this


def last_completed_session():
    """Date of the last completed US equity session, from SPY's daily bars."""
    now = datetime.now(ZoneInfo("America/New_York"))
    bars = yf.Ticker("SPY").history(period="10d")
    dates = [d.date() for d in bars.index]
    if dates and dates[-1] == now.date() and (now.hour, now.minute) < SESSION_CLOSE:
        dates = dates[:-1]  # today's session is still open
    if not dates:
        raise RuntimeError("could not determine last trading session")
    return dates[-1]


def main():
    force = "--force" in sys.argv
    session = last_completed_session().isoformat()
    out_dir = os.path.join(SNAP_DIR, session)
    if os.path.exists(out_dir) and not force:
        print(f"⏭️  Snapshot for {session} already exists ({out_dir}); use --force to overwrite.")
        return 0

    print(f"\n📸 Collecting snapshot for session {session}")
    print("=" * 70)
    start = time.time()
    results = {}
    for script in sorted(glob.glob(os.path.join(ROOT, "alpha_*", "main.py"))):
        alpha = os.path.basename(os.path.dirname(script))
        t0 = time.time()
        proc = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True)
        ok = proc.returncode == 0
        results[alpha] = ok
        tail = "" if ok else f" — {(proc.stderr or proc.stdout).strip().splitlines()[-1][:100]}"
        print(f"  {'✅' if ok else '❌'} {alpha} ({time.time() - t0:.0f}s){tail}")

    # Archive only files written by this run (skips stale outputs of removed alphas)
    fresh = [f for f in glob.glob(os.path.join(DATA_DIR, "*_latest.csv")) if os.path.getmtime(f) >= start]
    os.makedirs(out_dir, exist_ok=True)
    for f in fresh:
        shutil.copy2(f, os.path.join(out_dir, os.path.basename(f).replace("_latest", "")))

    n_ok = sum(results.values())
    print(f"\n{n_ok}/{len(results)} alphas succeeded; {len(fresh)} files archived to {os.path.relpath(out_dir, ROOT)}/")
    failed = [a for a, ok in results.items() if not ok]
    if failed:
        print(f"Failed: {', '.join(failed)}")
    return 0 if n_ok else 1


if __name__ == "__main__":
    sys.exit(main())
