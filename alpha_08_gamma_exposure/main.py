#!/usr/bin/env python3
"""Gamma Exposure (GEX) alpha signal.

Computes net gamma exposure of market makers from options open interest.
Signal = GEX level and GEX flip point (zero-gamma) vs spot price.

Positive GEX (long gamma) = MMs hedge by selling when up, buying when down → dampens moves.
Negative GEX (short gamma) = MMs hedge by buying when up, selling when down → amplifies moves.
GEX flip (zero gamma) = pin risk magnet, high gamma = volatility suppression zone.
"""

import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


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
        strike_prices = set()

        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                calls = chain.calls
                puts = chain.puts

                # Filter liquid options
                for df, opt_type in [(calls, 'call'), (puts, 'put')]:
                    df = df.copy()
                    df['volume'] = df['volume'].fillna(0).astype(int)
                    df['openInterest'] = df['openInterest'].fillna(0).astype(int)

                    liquid = df[
                        (df['volume'] > 10) | (df['openInterest'] > 100)
                    ].copy()

                    if len(liquid) == 0:
                        continue

                    # Gamma = OI * contract_size * gamma_per_contract
                    # yfinance provides 'gamma' but it may be NaN; compute approximation
                    # Gamma ≈ (normal_pdf(d1)) / (S * sigma * sqrt(T))
                    # For approximation: use provided gamma if available, else estimate

                    for _, row in liquid.iterrows():
                        strike = row['strike']
                        oi = row['openInterest']
                        gamma = row.get('gamma', np.nan)

                        if pd.isna(gamma) or gamma <= 0:
                            # Estimate gamma using Black-Scholes approximation
                            S = current_price
                            K = strike
                            T = dte / 252.0  # trading days
                            sigma = row.get('impliedVolatility', 0.2)
                            if pd.isna(sigma) or sigma <= 0:
                                sigma = 0.2

                            # d1 = (ln(S/K) + (r + 0.5*sigma^2)*T) / (sigma*sqrt(T))
                            # Assume r=0 for simplicity
                            if T <= 0:
                                continue
                            d1 = (np.log(S / K) + 0.5 * sigma**2 * T) / (sigma * np.sqrt(T))
                            # Standard normal PDF
                            pdf = np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi)
                            # Gamma = pdf / (S * sigma * sqrt(T))
                            gamma = pdf / (S * sigma * np.sqrt(T))

                        # GEX = OI * 100 * gamma * S^2 (dollar gamma per 1% move)
                        # Standard convention: GEX = OI * contract_size * gamma * S^2 / 100
                        contract_size = 100
                        gex = oi * contract_size * gamma * (current_price ** 2) / 100

                        # Calls: positive gamma (MMs long gamma if they sold calls)
                        # Puts: positive gamma (MMs long gamma if they sold puts)
                        # But OI is from buyer perspective; MMs are typically short
                        # Convention: Dealer GEX = -1 * OI * gamma * 100 * S^2 / 100
                        dealer_gex = -gex

                        total_gex += dealer_gex
                        gex_by_strike[strike] = gex_by_strike.get(strike, 0) + dealer_gex
                        gex_by_dte[dte] = gex_by_dte.get(dte, 0) + dealer_gex
                        strike_prices.add(strike)

            except Exception:
                continue

        if not gex_by_strike:
            return None

        # Find zero-gamma flip point (strike where cumulative GEX crosses zero)
        sorted_strikes = sorted(gex_by_strike.keys())
        cumulative = 0
        flip_strike = None
        for k in sorted_strikes:
            cumulative += gex_by_strike[k]
            if cumulative >= 0 and flip_strike is None:
                flip_strike = k
                break

        # Gamma at ATM
        atm_strike = min(gex_by_strike.keys(), key=lambda x: abs(x - current_price))
        atm_gex = gex_by_strike[atm_strike]

        # GEX per 1% move (normalized)
        gex_per_pct = total_gex / 100  # already in $ per 1% by convention

        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'total_gex': round(total_gex, 0),  # $ per 1% spot move
            'gex_per_pct': round(gex_per_pct, 0),
            'atm_strike': atm_strike,
            'atm_gex': round(atm_gex, 0),
            'flip_strike': flip_strike,
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
        print(f"  Zero-Gamma Flip:     ${flip:.0f} ({dist:+.2f}%)" if flip else "  Zero-Gamma Flip:     N/A")
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