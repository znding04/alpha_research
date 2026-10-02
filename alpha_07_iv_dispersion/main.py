#!/usr/bin/env python3
"""Index-Constituent IV Dispersion alpha signal.

Measures the spread between index ATM IV (SPY/QQQ) and the weighted
average of constituent ATM IVs (AAPL, MSFT, GOOGL, AMZN for SPY/QQQ).

Signal = Index IV - Weighted Constituent IV
- Positive dispersion → Index options expensive vs singles (fear/hedging demand)
- Negative dispersion → Index options cheap vs singles (complacency)

Cross-sectionally: High dispersion tickers → mean reversion opportunity.
Pairs well with: VRP (alpha_04), IV Skew (alpha_02), IV Term Structure (alpha_03).
"""

import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime


TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]

# SPY weights (approximate top 4 holdings as of 2024)
SPY_WEIGHTS = {
    "AAPL": 0.07,
    "MSFT": 0.06,
    "GOOGL": 0.035,  # GOOG + GOOGL combined ~3.5%
    "AMZN": 0.035,
}

# QQQ weights (approximate top 4 holdings)
QQQ_WEIGHTS = {
    "AAPL": 0.12,
    "MSFT": 0.10,
    "GOOGL": 0.06,
    "AMZN": 0.05,
}


def compute_atm_iv(ticker_str, target_dte_range=(14, 60)):
    """Get ATM IV from nearest liquid expiration within target DTE range."""
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

        # Use nearest valid expiration
        target_exp, dte = valid_exps[0]
        target_str = target_exp.strftime("%Y-%m-%d")

        chain = tq.option_chain(target_str)
        calls = chain.calls
        puts = chain.puts

        # Filter liquid options
        calls = calls[
            (calls['volume'].fillna(0) > 10) | (calls['openInterest'].fillna(0) > 100)
        ].copy()
        puts = puts[
            (puts['volume'].fillna(0) > 10) | (puts['openInterest'].fillna(0) > 100)
        ].copy()

        if len(calls) < 5 or len(puts) < 5:
            return None, current_price

        # Find ATM strike - use most liquid strike near ATM
        all_options = pd.concat([calls, puts], ignore_index=True)

        # Define moneyness range: strikes within 5% of spot
        moneyness_low = current_price * 0.95
        moneyness_high = current_price * 1.05
        near_atm = all_options[
            (all_options['strike'] >= moneyness_low) &
            (all_options['strike'] <= moneyness_high)
        ].copy()

        if len(near_atm) == 0:
            return None, current_price

        # Filter for liquid options with valid IV > 0.01 (1%)
        near_atm = near_atm[
            (near_atm['volume'].fillna(0) > 10) | (near_atm['openInterest'].fillna(0) > 100)
        ].copy()
        near_atm = near_atm[
            (near_atm['impliedVolatility'].notna()) &
            (near_atm['impliedVolatility'] > 0.01)
        ].copy()

        if len(near_atm) == 0:
            return None, current_price

        # Weighted average IV by liquidity
        near_atm['liquidity'] = near_atm['volume'].fillna(0) + near_atm['openInterest'].fillna(0)
        total_liq = near_atm['liquidity'].sum()
        if total_liq > 0:
            atm_iv = (near_atm['impliedVolatility'] * near_atm['liquidity']).sum() / total_liq
        else:
            atm_iv = near_atm['impliedVolatility'].median()

        return atm_iv, current_price

    except Exception as e:
        print(f"  ⚠️ {ticker_str} ATM IV: {type(e).__name__}: {e}")
        return None, None


def compute_dispersion_metrics(ticker_str, index_ticker, index_weights):
    """Compute IV dispersion for index vs constituents."""
    # Get index ATM IV
    index_iv, index_price = compute_atm_iv(index_ticker)
    if index_iv is None or pd.isna(index_iv) or index_iv <= 0:
        return None

    # Get constituent ATM IVs
    constituent_ivs = {}
    constituent_prices = {}
    for const_ticker, weight in index_weights.items():
        const_iv, const_price = compute_atm_iv(const_ticker)
        if const_iv is not None and not pd.isna(const_iv) and const_iv > 0:
            constituent_ivs[const_ticker] = const_iv
            constituent_prices[const_ticker] = const_price

    if len(constituent_ivs) < 2:
        return None

    # Compute weighted average constituent IV
    # Normalize weights to sum to 1 for available constituents
    available_weights = {k: v for k, v in index_weights.items() if k in constituent_ivs}
    weight_sum = sum(available_weights.values())
    if weight_sum == 0:
        return None

    normalized_weights = {k: v / weight_sum for k, v in available_weights.items()}

    weighted_const_iv = sum(
        constituent_ivs[k] * normalized_weights[k]
        for k in constituent_ivs
    )

    # Dispersion = Index IV - Weighted Constituent IV
    dispersion = index_iv - weighted_const_iv

    # Also compute dispersion as ratio
    dispersion_ratio = index_iv / weighted_const_iv if weighted_const_iv > 0 else np.nan

    # Z-score of dispersion if we had history (placeholder for now)
    # This would need historical dispersion tracking like alpha_05

    return {
        'index': index_ticker,
        'index_price': round(index_price, 2),
        'index_atm_iv': round(index_iv, 4),
        'constituent_ivs': {k: round(v, 4) for k, v in constituent_ivs.items()},
        'constituent_prices': {k: round(v, 2) for k, v in constituent_prices.items()},
        'weighted_const_iv': round(weighted_const_iv, 4),
        'dispersion': round(dispersion, 6),
        'dispersion_ratio': round(dispersion_ratio, 4),
        'n_constituents': len(constituent_ivs),
    }


if __name__ == "__main__":
    print(f"\n📊 IV Dispersion Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []

    # SPY dispersion
    spy_result = compute_dispersion_metrics("SPY", "SPY", SPY_WEIGHTS)
    if spy_result:
        spy_result['index_name'] = "SPY"
        results.append(spy_result)

    # QQQ dispersion
    qqq_result = compute_dispersion_metrics("QQQ", "QQQ", QQQ_WEIGHTS)
    if qqq_result:
        qqq_result['index_name'] = "QQQ"
        results.append(qqq_result)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        disp = r['dispersion']
        ratio = r['dispersion_ratio']
        disp_str = f"{disp:.6f}"
        ratio_str = f"{ratio:.4f}" if not pd.isna(ratio) else "N/A"

        # Interpretation
        if disp > 0.02:
            signal = "🔴 HIGH DISPERSION — Index IV expensive vs constituents (sell index vol / buy single-stock vol)"
        elif disp > 0.005:
            signal = "🟠 POSITIVE DISPERSION — Index IV premium"
        elif disp < -0.02:
            signal = "🟢 NEGATIVE DISPERSION — Index IV cheap vs constituents (buy index vol / sell single-stock vol)"
        elif disp < -0.005:
            signal = "🔵 SLIGHT NEGATIVE — Index IV discount"
        else:
            signal = "⚪ NEUTRAL — Minimal dispersion"

        print(f"\n{r['index_name']} (${r['index_price']}):")
        print(f"  Index ATM IV:           {r['index_atm_iv']:.4f}")
        print(f"  Weighted Constituent IV: {r['weighted_const_iv']:.4f}")
        print(f"  Dispersion (Index - Wtd): {disp_str}")
        print(f"  Dispersion Ratio:       {ratio_str}")
        print(f"  Constituents:")
        for const in sorted(r['constituent_ivs'].keys()):
            print(f"    {const}: IV={r['constituent_ivs'][const]:.4f} (${r['constituent_prices'][const]:.2f})")
        print(f"  Signal:                 {signal}")

    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_dispersion_latest.csv"

    flat_rows = []
    for r in results:
        base = {
            'index': r['index'],
            'index_price': r['index_price'],
            'index_atm_iv': r['index_atm_iv'],
            'weighted_const_iv': r['weighted_const_iv'],
            'dispersion': r['dispersion'],
            'dispersion_ratio': r['dispersion_ratio'],
            'n_constituents': r['n_constituents'],
        }
        for const, iv in r['constituent_ivs'].items():
            row = base.copy()
            row['constituent'] = const
            row['constituent_iv'] = iv
            row['constituent_price'] = r['constituent_prices'][const]
            flat_rows.append(row)

    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")