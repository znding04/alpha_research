#!/usr/bin/env python3
"""IV Rank Percentile alpha signal — cross-sectional vol price ranking.

Computes current ATM IV percentile rank vs ~1-year historical range per ticker.
Signal = percentile of current IV within historical distribution.
High percentile (IV expensive) → mean reversion sell vol / equity underperformance.
Low percentile (IV cheap) → mean reversion buy vol / equity outperformance.
"""
import os
import warnings
warnings.filterwarnings('ignore')

import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]
HISTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "iv_history.json")


def compute_atm_iv(ticker_str, target_dte_range=(14, 60)):
    """Get liquidity-weighted ATM IV from nearest expiration in DTE range."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            return None, None

        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if target_dte_range[0] <= dte <= target_dte_range[1]:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None, current_price

        target_exp, dte = valid_exps[0]
        target_str = target_exp.strftime("%Y-%m-%d")

        chain = tq.option_chain(target_str)
        calls = chain.calls
        puts = chain.puts

        calls = calls[
            (calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)
        ].copy()
        puts = puts[
            (puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)
        ].copy()

        if len(calls) < 5 or len(puts) < 5:
            return None, current_price

        all_options = pd.concat([calls, puts], ignore_index=True)

        moneyness_low = current_price * 0.95
        moneyness_high = current_price * 1.05
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low) &
            (all_options['strike'] <= moneyness_high)
        ].copy()

        if len(near_atm) == 0:
            return None, current_price

        near_atm = near_atm[
            (near_atm['volume'].fillna(0) > 10) | (near_atm['openInterest'].fillna(0) > 100)
        ].copy()
        near_atm = near_atm[
            (near_atm['impliedVolatility'].notna()) &
            (near_atm['impliedVolatility'] > 0.01)
        ].copy()

        if len(near_atm) == 0:
            return None, current_price

        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = float((near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq)
        else:
            atm_iv = float(near_atm['impliedVolatility'].median())

        return atm_iv, current_price

    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return None, None


def load_iv_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_iv_history(history):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, 'w') as f:
        json.dump(history, f, indent=2)


def update_iv_history(history, ticker_str, atm_iv, current_price):
    today = datetime.now().strftime("%Y-%m-%d")
    if ticker_str not in history:
        history[ticker_str] = []
    existing_dates = [entry['date'] for entry in history[ticker_str]]
    if today not in existing_dates:
        history[ticker_str].append({
            'date': today,
            'atm_iv': round(atm_iv, 6),
            'price': round(current_price, 2),
        })
    cutoff_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    history[ticker_str] = [e for e in history[ticker_str] if e['date'] >= cutoff_date]
    return history


def compute_iv_percentile(history, ticker_str, current_iv):
    if ticker_str not in history or len(history[ticker_str]) < 10:
        return np.nan, np.nan, len(history.get(ticker_str, []))

    historical_ivs = [e['atm_iv'] for e in history[ticker_str]]
    percentile = float((np.sum(np.array(historical_ivs) <= current_iv) / len(historical_ivs)) * 100)
    hist_mean = np.mean(historical_ivs)
    hist_std = np.std(historical_ivs)
    z_score = float((current_iv - hist_mean) / hist_std) if hist_std > 0 else np.nan
    return percentile, z_score, len(historical_ivs)


def compute_iv_rank_percentile_metrics(ticker_str):
    atm_iv, current_price = compute_atm_iv(ticker_str)
    if atm_iv is None or pd.isna(atm_iv) or atm_iv <= 0:
        return None

    history = load_iv_history()
    history = update_iv_history(history, ticker_str, atm_iv, current_price)
    save_iv_history(history)

    percentile, z_score, n_obs = compute_iv_percentile(history, ticker_str, atm_iv)

    if ticker_str in history and len(history[ticker_str]) > 0:
        hist_ivs = [e['atm_iv'] for e in history[ticker_str]]
        hist_min = min(hist_ivs)
        hist_max = max(hist_ivs)
        hist_mean = np.mean(hist_ivs)
        hist_median = np.median(hist_ivs)
    else:
        hist_min = hist_max = hist_mean = hist_median = np.nan

    return {
        'ticker': ticker_str,
        'current_price': round(current_price, 2),
        'atm_iv': round(atm_iv, 4),
        'iv_percentile': round(percentile, 1) if not pd.isna(percentile) else np.nan,
        'iv_zscore': round(z_score, 2) if not pd.isna(z_score) else np.nan,
        'hist_min_iv': round(hist_min, 4) if not pd.isna(hist_min) else np.nan,
        'hist_max_iv': round(hist_max, 4) if not pd.isna(hist_max) else np.nan,
        'hist_mean_iv': round(hist_mean, 4) if not pd.isna(hist_mean) else np.nan,
        'hist_median_iv': round(hist_median, 4) if not pd.isna(hist_median) else np.nan,
        'n_observations': n_obs,
    }


if __name__ == "__main__":
    print(f"\n📊 IV Rank Percentile Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_iv_rank_percentile_metrics(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    for r in results:
        pct = r['iv_percentile']
        z = r['iv_zscore']
        pct_str = f"{pct:.1f}%" if not pd.isna(pct) else "N/A (building history)"
        z_str = f"{z:.2f}" if not pd.isna(z) else "N/A"

        if not pd.isna(pct):
            if pct >= 80:
                signal = "🔴 HIGH IV — Expensive vol, mean reversion DOWN likely"
            elif pct >= 60:
                signal = "🟠 ELEVATED IV — Above average"
            elif pct <= 20:
                signal = "🟢 LOW IV — Cheap vol, mean reversion UP likely"
            elif pct <= 40:
                signal = "🔵 DEPRESSED IV — Below average"
            else:
                signal = "⚪ NEUTRAL IV — Near historical median"
        else:
            signal = "⏳ Building history..."

        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  ATM IV (ann.):      {r['atm_iv']:.4f}")
        print(f"  IV Percentile:      {pct_str}")
        print(f"  IV Z-Score:         {z_str}")
        print(f"  Historical Range:   {r['hist_min_iv']:.4f} – {r['hist_max_iv']:.4f}")
        print(f"  Hist Mean/Median:   {r['hist_mean_iv']:.4f} / {r['hist_median_iv']:.4f}")
        print(f"  Observations:       {r['n_observations']}")
        print(f"  Signal:             {signal}")

    # Cross-sectional ranking by IV percentile
    valid = [r for r in results if not pd.isna(r['iv_percentile'])]
    if len(valid) >= 2:
        ranked = sorted(valid, key=lambda x: x['iv_percentile'])
        print("\n🏆 Cross-sectional IV Percentile Rank (cheapest → most expensive):")
        for i, r in enumerate(ranked):
            print(f"  #{i+1:2d} {r['ticker']:6s}  {r['iv_percentile']:.1f}%  (IV={r['atm_iv']:.4f})")

    os.makedirs(os.path.dirname(os.path.abspath(__file__)) + "/../data", exist_ok=True)
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "iv_percentile_latest.csv")
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   History stored in {HISTORY_PATH}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")