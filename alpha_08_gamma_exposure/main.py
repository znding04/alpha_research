#!/usr/bin/env python3
"""Gamma Exposure (GEX) alpha signal.

Computes net gamma exposure of market makers from options open interest.
Signal = GEX level and GEX flip point (zero-gamma) vs spot price.

Positive GEX (long gamma) = MMs hedge by selling when up, buying when down → dampens moves.
Negative GEX (short gamma) = MMs hedge by buying when up, selling when down → amplifies moves.
GEX flip (zero gamma) = pin risk magnet, high gamma = volatility suppression zone.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

from common.universe import TICKERS


def bs_gamma(S, K, T, sigma):
    """Black-Scholes gamma (r = q = 0); vectorised over S."""
    d1 = (np.log(S / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
    pdf = np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi)
    return pdf / (S * sigma * np.sqrt(T))


def find_zero_gamma(contracts, spot, width=0.20, n=401):
    """Spot level nearest current spot where total dealer GEX crosses zero (None if no crossing)."""
    if not contracts:
        return None
    K, T, sig, oi, sign = (np.array(c, dtype=float) for c in zip(*contracts))
    grid = np.linspace(spot * (1 - width), spot * (1 + width), n)
    gex = np.array([(sign * bs_gamma(s, K, T, sig) * oi * 100 * s**2 * 0.01).sum() for s in grid])
    crossings = np.where(np.sign(gex[:-1]) != np.sign(gex[1:]))[0]
    if len(crossings) == 0:
        return None
    # Linear interpolation at each crossing; keep the one closest to spot
    levels = [grid[i] - gex[i] * (grid[i + 1] - grid[i]) / (gex[i + 1] - gex[i]) for i in crossings]
    return float(min(levels, key=lambda x: abs(x - spot)))


def compute_gamma_exposure(ticker_str, max_dte=45):
    """Compute GEX metrics for a single ticker from option chain open interest."""
    try:
        tq = yf.Ticker(ticker_str)

        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')

        if current_price is None or current_price <= 0:
            return None

        # Get all valid expirations within max_dte
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 1 <= dte <= max_dte:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])

        if not valid_exps:
            return None

        total_gex = 0.0
        gex_by_strike = {}
        gex_by_dte = {}
        contracts = []  # (strike, T, sigma, oi, sign) for the zero-gamma spot sweep

        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                calls = chain.calls
                puts = chain.puts

                # Standard dealer convention (SqueezeMetrics-style): customers sell calls
                # (overwriting) and buy puts (hedging), so dealers are LONG call gamma and
                # SHORT put gamma → call GEX positive, put GEX negative.
                for df, sign in [(calls, 1.0), (puts, -1.0)]:
                    df = df.copy()
                    df['volume'] = df['volume'].fillna(0).astype(int)
                    df['openInterest'] = df['openInterest'].fillna(0).astype(int)

                    liquid = df[
                        ((df['volume'] > 10) | (df['openInterest'] > 100)) &
                        (df['openInterest'] > 0)
                    ].copy()

                    if len(liquid) == 0:
                        continue

                    # Calendar time to expiry (DTE counts calendar days)
                    T = dte / 365.0
                    for _, row in liquid.iterrows():
                        strike = row['strike']
                        oi = row['openInterest']
                        sigma = row.get('impliedVolatility', np.nan)
                        # yfinance has no gamma column; skip placeholder IVs (after-hours / 0-DTE)
                        if pd.isna(sigma) or sigma < 0.05 or sigma > 3.0:
                            continue

                        gamma = bs_gamma(current_price, strike, T, sigma)
                        # GEX = gamma × OI × 100 × S² × 0.01 → dealer $ delta change per 1% spot move
                        dealer_gex = sign * gamma * oi * 100 * current_price ** 2 * 0.01

                        total_gex += dealer_gex
                        gex_by_strike[strike] = gex_by_strike.get(strike, 0) + dealer_gex
                        gex_by_dte[dte] = gex_by_dte.get(dte, 0) + dealer_gex
                        contracts.append((strike, T, sigma, oi, sign))

            except Exception:
                continue

        if not gex_by_strike:
            return None

        # Zero-gamma flip: spot level where total dealer GEX changes sign,
        # recomputing every contract's gamma at hypothetical spots (±20%).
        flip_strike = find_zero_gamma(contracts, current_price)

        # Gamma at ATM
        atm_strike = min(gex_by_strike.keys(), key=lambda x: abs(x - current_price))
        atm_gex = gex_by_strike[atm_strike]

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'total_gex': round(total_gex, 0),  # $ per 1% spot move
            'atm_strike': atm_strike,
            'atm_gex': round(atm_gex, 0),
            'flip_strike': round(flip_strike, 2) if flip_strike else None,
            'distance_to_flip_pct': round((flip_strike - current_price) / current_price * 100, 2) if flip_strike else np.nan,
            'n_expirations': len(valid_exps),
            'gex_by_strike': {str(k): round(v, 0) for k, v in sorted(gex_by_strike.items())},
            'gex_by_dte': {str(k): round(v, 0) for k, v in sorted(gex_by_dte.items())},
        }

    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 Gamma Exposure (GEX) Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    results = []
    for t in TICKERS:
        r = compute_gamma_exposure(t)
        if r:
            results.append(r)

    if not results:
        print("No data collected.")
        exit(1)

    # Print summary
    for r in results:
        flip = r['flip_strike']
        dist = r['distance_to_flip_pct']
        gex_sign = "🟢 Long Gamma" if r['total_gex'] > 0 else "🔴 Short Gamma"
        print(f"\n{r['ticker']} (${r['current_price']}):")
        print(f"  Total GEX ($/1%):    {r['total_gex']:,.0f}  ({gex_sign})")
        print(f"  ATM Strike GEX:      {r['atm_gex']:,.0f}")
        print(f"  Zero-Gamma Flip:     ${flip:.2f} ({dist:+.2f}%)" if flip else "  Zero-Gamma Flip:     none within ±20%")
        print(f"  Expirations used:    {r['n_expirations']}")

    # Save detailed data
    os.makedirs("data", exist_ok=True)
    path = "data/gamma_exposure_latest.csv"

    # Flatten for CSV
    flat_rows = []
    for r in results:
        for strike, gex in r['gex_by_strike'].items():
            flat_rows.append({
                'ticker': r['ticker'],
                'current_price': r['current_price'],
                'strike': float(strike),
                'gex': gex,
                'total_gex': r['total_gex'],
                'flip_strike': r['flip_strike'],
                'distance_to_flip_pct': r['distance_to_flip_pct'],
            })

    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved detailed data to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")