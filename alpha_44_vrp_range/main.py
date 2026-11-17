#!/usr/bin/env python3
"""VRP with Parkinson (range-based) realized volatility — alpha_44.

Signal: Variance Risk Premium estimated against a RANGE-based realized vol
instead of the usual close-to-close RV.

    VRP_range = ATM_IV^2 - RV_parkinson^2

Why a new variant: every existing VRP alpha in this repo (01, 04, 21, 23, 33,
34, 38, 39, 41) uses close-to-close realized volatility. The close-to-close
estimator throws away the intraday high/low and is ~5x less statistically
efficient than a range estimator (Parkinson 1980; Garman-Klass 1980). A more
efficient RV estimate means a *less noisy* realized-variance benchmark, so the
implied-minus-realized gap is a cleaner read on whether options are rich or
cheap.

    Parkinson (1980):  sigma^2 = (1 / (4 ln 2)) * mean[ (ln(H/L))^2 ]
    Garman-Klass (1980): sigma^2 = 0.5*(ln(H/L))^2 - (2 ln2 - 1)*(ln(C/O))^2

Both are annualized by * 252. Garman-Klass is reported as a robustness check;
Parkinson is the primary estimator because it is insensitive to overnight gaps
(yfinance daily bars can have split/gap artifacts) and needs only H/L.

Interpretation
    VRP_range > 0  -> options expensive vs realized (vol risk premium rich)
    VRP_range < 0  -> options cheap vs realized (stress / underpriced vol)
Cross-sectionally: rank the 6 focus names by VRP_range. High = expensive vol,
low = cheap vol. Hypothesis: the cross-sectional rank predicts forward returns.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

from common.universe import TICKERS

# Focus cross-section requested for this signal (subset of TICKERS).
FOCUS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]

RV_WINDOW = 60          # trading days for the range estimator
MIN_RV_OBS = 30


def get_atm_iv(ticker_str, target_dte_range=(14, 90)):
    """Robust ATM IV from the nearest liquid expiration within target DTE range.

    Returns (atm_iv, current_price, n_contracts) or (None, None, None) on failure.
    """
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None, None, None

        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if target_dte_range[0] <= dte <= target_dte_range[1]:
                    valid_exps.append(d)
            except ValueError:
                continue
        valid_exps.sort()
        if not valid_exps:
            return None, None, None

        target_exp = min(
            [e for e in valid_exps if e > datetime.now().replace(day=max(now.day, 2))],
            default=valid_exps[0],
        )
        chain = tq.option_chain(target_exp.strftime("%Y-%m-%d"))
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)

        # volume/OI are numpy int64; fillna + astype(int) for safe comparison.
        df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)

        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()

        if len(df) < 10:
            return None, None, None

        moneyness = df['strike'] / current_price
        atm_cand = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
        if len(atm_cand) >= 3:
            atm_iv = atm_cand['impliedVolatility'].median()
        else:
            valid = df[df['impliedVolatility'] > 0.05]
            if len(valid) == 0:
                return None, None, None
            idx = (valid['strike'] - current_price).abs().idxmin()
            atm_iv = valid.loc[idx, 'impliedVolatility']

        return round(float(atm_iv), 4), round(float(current_price), 2), int(len(df))

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None, None, None


def compute_range_vol(ticker_str, window=RV_WINDOW):
    """Parkinson + Garman-Klass annualized realized vol from OHLC bars.

    Returns dict with parkinson, garman_klass, n_obs or None on failure.
    """
    try:
        hist = yf.Ticker(ticker_str).history(period="1y", interval="1d")
        if hist.empty:
            return None
        hist = hist.dropna(subset=['High', 'Low', 'Close'])
        if len(hist) < MIN_RV_OBS:
            return None

        h = hist['High'].values
        l = hist['Low'].values
        c = hist['Close'].values
        o = hist['Open'].values if 'Open' in hist else c

        # Guard against zero/negative prices in the range ratios.
        ok = (h > 0) & (l > 0) & (c > 0) & (o > 0)
        h, l, c, o = h[ok], l[ok], c[ok], o[ok]
        if len(h) < MIN_RV_OBS:
            return None

        log_hl = np.log(h / l)
        log_co = np.log(c / o)

        # Use the most recent `window` bars.
        n = min(window, len(log_hl))
        log_hl = log_hl[-n:]
        log_co = log_co[-n:]

        park_var = float(np.mean(log_hl ** 2) / (4.0 * np.log(2.0)))
        gk_var = float(np.mean(0.5 * log_hl ** 2 - (2.0 * np.log(2.0) - 1.0) * log_co ** 2))

        park = np.sqrt(max(park_var, 0.0) * 252)
        gk = np.sqrt(max(gk_var, 0.0) * 252)
        return {"parkinson": round(park, 4), "garman_klass": round(gk, 4), "n_obs": int(n)}
    except Exception:
        return None


def compute_signal(ticker_str):
    """Return dict with VRP_range signal for a single ticker."""
    atm_iv, price, n_contracts = get_atm_iv(ticker_str)
    if atm_iv is None:
        return None
    rv = compute_range_vol(ticker_str)
    if rv is None or rv["parkinson"] <= 0:
        return None

    rv_p = rv["parkinson"]
    rv_gk = rv["garman_klass"]
    vrp = atm_iv ** 2 - rv_p ** 2
    vrp_ratio = vrp / rv_p ** 2 if rv_p > 0 else np.nan

    return {
        "ticker": ticker_str,
        "current_price": price,
        "atm_iv": atm_iv,
        "rv_parkinson": rv_p,
        "rv_garman_klass": rv_gk,
        "vrp_range": round(vrp, 6),
        "vrp_ratio_range": round(float(vrp_ratio), 4) if np.isfinite(vrp_ratio) else np.nan,
        "n_contracts": n_contracts,
        "n_rv_obs": rv["n_obs"],
    }


if __name__ == "__main__":
    print(f"\n🔍 VRP-Range (Parkinson RV) Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 74)

    results = []
    for t in TICKERS:
        r = compute_signal(t)
        if r:
            results.append(r)
            print(f"  ✅ {t}: VRP_range={r['vrp_range']:+.6f} "
                  f"(IV={r['atm_iv']:.4f}, RV_park={r['rv_parkinson']:.4f}, "
                  f"RV_gk={r['rv_garman_klass']:.4f})")
        else:
            print(f"  ⚠️ {t}: no data")

    if not results:
        print("No data collected.")
        sys.exit(1)

    df = pd.DataFrame(results)

    # Cross-sectional rank over the focus subset (higher VRP = richer vol).
    focus_df = df[df['ticker'].isin(FOCUS)].copy()
    if len(focus_df) >= 2:
        focus_df['vrp_rank'] = focus_df['vrp_range'].rank(ascending=True, pct=True)
        rank_map = dict(zip(focus_df['ticker'], focus_df['vrp_rank']))
        df['vrp_rank'] = df['ticker'].map(rank_map)

    print("\n" + df.to_string(index=False))
    print("\n💡 Interpretation:")
    print("   VRP_range > 0 → options expensive vs range-realized vol (rich premium)")
    print("   VRP_range < 0 → options cheap vs range-realized vol (stress / cheap vol)")
    print("   vrp_rank: cross-sectional percentile over the 6 focus names (1 = richest vol)")

    os.makedirs("data", exist_ok=True)
    path = "data/vrp_range_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
