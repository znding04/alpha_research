#!/usr/bin/env python3
"""
IV Surface Explorer — Pull real-time options IV surface for analysis.
Generates IV smile/skew plots and term structure visualization.
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ─── Config ───────────────────────────────────────────────────────────────────
TICKER = "AAPL"


def get_iv_surface(ticker_str="AAPL", max_days_to_expiry=90):
    """Fetch full IV surface for a ticker."""
    tq = yf.Ticker(ticker_str)
    expirations = list(tq.options)

    # Filter: remove very short-dated (intraday risk) and very far out (>max_days)
    now = datetime.now()
    cutoff = now + timedelta(days=max_days_to_expiry)
    valid_exps = []
    for e in expirations:
        try:
            exp_date = datetime.strptime(e, "%Y-%m-%d")
            if now.date() < exp_date.date() <= cutoff.date():
                valid_exps.append(e)
        except ValueError:
            continue
    valid_exps.sort()

    all_data = {"calls": [], "puts": []}

    for exp in valid_exps[:12]:  # cap at 12 to avoid timeout
        try:
            chain = tq.option_chain(exp)
            calls = chain.calls.copy()
            puts = chain.puts.copy()

            calls["expiration"] = exp
            calls["contract_type"] = "call"
            puts["expiration"] = exp
            puts["contract_type"] = "put"

            dte = (datetime.strptime(exp, "%Y-%m-%d") - now).days
            calls["dte"] = dte
            puts["dte"] = dte

            all_data["calls"].append(calls)
            all_data["puts"].append(puts)
        except Exception:
            continue

    if not all_data["calls"]:
        return None, None

    df_calls = pd.concat(all_data["calls"], ignore_index=True)
    df_puts = pd.concat(all_data["puts"], ignore_index=True)

    return df_calls, df_puts


def filter_quality(df, min_volume=10, min_oi=100):
    """Filter out illiquid contracts."""
    vol_mask = ((df['volume'] > min_volume) | (df['openInterest'] > min_oi))
    iv_valid = (df['impliedVolatility'].notna()) & (df['impliedVolatility'] > 0)
    valid_strike = (df['strike'] > 0)
    good_price = (df['lastPrice'] > 0)
    return df[(vol_mask & iv_valid & valid_strike & good_price)].copy()


def plot_iv_smile(df_all, stock_price, output_dir="figures"):
    """Plot IV vs moneyness for a single expiration."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    os.makedirs(output_dir, exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, ct in zip(axes, ['call', 'put']):
        subset = df_all[df_all['contract_type'] == ct].dropna(subset=['impliedVolatility'])
        if len(subset) < 5:
            continue

        x = subset['strike'] / stock_price  # moneyness ratio
        y = subset['impliedVolatility'].clip(0, 2)  # cap IV at 200%

        # Scatter
        ax.scatter(x, y, alpha=0.6, s=20, label='IV points')

        # Smooth via rolling median
        if len(x) > 5:
            sorted_idx = np.argsort(x.values)
            sort_x = x.values[sorted_idx]
            sort_y = y.values[sorted_idx]

            window = min(7, max(3, len(sort_x) // 6))
            smoothed = pd.Series(sort_y).rolling(window, center=True, min_periods=3).median().values
            ax.plot(sort_x, smoothed, '-', linewidth=2, label=f'{ct.title()} curve')

        atm_moneyness = stock_price / stock_price  # = 1.0
        ax.axvline(atm_moneyness, color='gray', linestyle='--', alpha=0.5, label='ATM')
        ax.set_xlabel('Strike / Stock Price (Moneyness)')
        ax.set_ylabel('Implied Volatility')
        ax.set_title(f'{ct.title()} IV vs Moneyness')
        ax.legend()
        ax.grid(True, alpha=0.3)

    fig.suptitle(f'{TICKER} IV Smile/Skew', fontsize=14, fontweight='bold')
    plt.tight_layout()
    path = f"{output_dir}/iv_smile_{TICKER.lower()}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    print(f"Saved: {path}")
    plt.close()


def plot_iv_term_structure(df_all, stock_price, output_dir="figures"):
    """Plot IV vs DTE at constant moneyness levels."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    os.makedirs(output_dir, exist_ok=True)

    # Pick target moneyness levels for puts and calls separately
    put_levels = [0.85, 0.90, 0.95]   # OTM puts below ATM
    call_levels = [1.05, 1.10, 1.15]  # OTM calls above ATM

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Plot 1: Put IV Term Structure
    ax_put = axes[0]
    for level in put_levels:
        strike_target = stock_price * level
        mask = (
            (df_all['contract_type'] == 'put') &
            (df_all['strike'].between(strike_target * 0.95, strike_target * 1.05)) &
            (df_all['impliedVolatility'].notna()) &
            (df_all['impliedVolatility'] > 0) &
            (df_all['impliedVolatility'] < 3.0) &
            (df_all['dte'] > 0) &
            (df_all['dte'] < 180)
        )
        subset = df_all[mask]

        if len(subset) >= 2:
            ax_put.scatter(subset['dte'], subset['impliedVolatility'],
                         s=40, alpha=0.7, label=f'{level:.2f}')
            if len(subset) > 3:
                ax_put.plot(subset['dte'].sort_values(),
                          subset['impliedVolatility'].sort_values().rolling(3).mean(),
                          '-', alpha=0.5, linewidth=1.5)

    ax_put.set_title(f'{TICKER} Put IV Term Structure')
    ax_put.set_xlabel('Days to Expiry (DTE)')
    ax_put.set_ylabel('Implied Volatility')
    ax_put.legend(title='Strike Level (OTM %)')
    ax_put.grid(True, alpha=0.3)

    # Plot 2: Call IV Term Structure
    ax_call = axes[1]
    for level in call_levels:
        strike_target = stock_price * level
        mask = (
            (df_all['contract_type'] == 'call') &
            (df_all['strike'].between(strike_target * 0.95, strike_target * 1.05)) &
            (df_all['impliedVolatility'].notna()) &
            (df_all['impliedVolatility'] > 0) &
            (df_all['impliedVolatility'] < 3.0) &
            (df_all['dte'] > 0) &
            (df_all['dte'] < 180)
        )
        subset = df_all[mask]

        if len(subset) >= 2:
            ax_call.scatter(subset['dte'], subset['impliedVolatility'],
                          s=40, alpha=0.7, label=f'{level:.2f}')
            if len(subset) > 3:
                ax_call.plot(subset['dte'].sort_values(),
                           subset['impliedVolatility'].sort_values().rolling(3).mean(),
                           '-', alpha=0.5, linewidth=1.5)

    ax_call.set_title(f'{TICKER} Call IV Term Structure')
    ax_call.set_xlabel('Days to Expiry (DTE)')
    ax_call.set_ylabel('Implied Volatility')
    ax_call.legend(title='Strike Level (OTM %)')
    ax_call.grid(True, alpha=0.3)

    fig.suptitle(f'{TICKER} IV Term Structure', fontsize=14, fontweight='bold')
    plt.tight_layout()
    path = f"{output_dir}/iv_term_structure_{TICKER.lower()}.png"
    plt.savefig(path, dpi=150, bbox_inches='tight')
    print(f"Saved: {path}")
    plt.close()


# ─── Main Exploration ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Fetching IV surface for {TICKER}...")

    try:
        df_calls, df_puts = get_iv_surface(TICKER, max_days_to_expiry=90)

        if df_calls is None or df_puts is None:
            print("❌ No option data available.")
            exit(1)

        # Combine
        df_all = pd.concat([df_calls, df_puts], ignore_index=True)

        # Get stock price
        tq = yf.Ticker(TICKER)
        info = tq.info
        stock_price = info.get('currentPrice') or info.get('regularMarketPrice')
        print(f"\nStock price: ${stock_price:.2f}")

        # Filter low quality
        df_all = filter_quality(df_all, min_volume=5, min_oi=10)
        print(f"After quality filter: {len(df_all)} contracts")

        # Summary statistics
        n_exps = df_all['expiration'].nunique()
        print(f"Expirations included: {n_exps}")

        call_sum = df_all[df_all['contract_type'] == 'call']['impliedVolatility'].describe()
        put_sum = df_all[df_all['contract_type'] == 'put']['impliedVolatility'].describe()

        print(f"\n=== CALL IV Summary ===")
        print(call_sum.round(4))
        print(f"\n=== PUT IV Summary ===")
        print(put_sum.round(4))

        # Quick skew check: compare IV of near-OTM puts vs calls
        put_25delta = df_all[(df_all['contract_type'] == 'put') & (df_all['strike'] < stock_price)]
        call_25delta = df_all[(df_all['contract_type'] == 'call') & (df_all['strike'] > stock_price)]

        if len(put_25delta) > 0 and len(call_25delta) > 0:
            avg_put_iv = put_25delta['impliedVolatility'].median()
            avg_call_iv = call_25delta['impliedVolatility'].median()
            skew = avg_put_iv - avg_call_iv
            print(f"\n📊 OTM Put-Call Skew (near 25-delta): {skew:+.4f}")
            if skew > 0:
                print("   → Positive skew = market paying more for downside protection (normal)")
            elif skew < 0:
                print("   → Negative skew = calls pricier than puts (bullish sentiment)")

        # Plot
        print("\nGenerating figures...")
        plot_iv_smile(df_all, stock_price, output_dir="figures")
        plot_iv_term_structure(df_all, stock_price, output_dir="figures")

        print("\n✅ Exploration complete!")
        print(f"Figures saved in figures/")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
