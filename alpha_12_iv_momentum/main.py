#!/usr/bin/env python3
"""IV Momentum alpha signal.

Tracks short-term ATM IV trend (momentum) as a predictor of forward returns.
Signal = recent IV change (e.g., 5-day) vs. subsequent returns.

Rationale: Rising IV often precedes downside (fear buying); falling IV often precedes upside (complacency).
But extreme IV momentum can also signal mean reversion in IV itself.
"""
import os
os.environ.setdefault("PYTHONPATH", "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import json

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]

HISTORY_FILE = "data/iv_momentum_history.json"
LOOKBACK_DAYS = 5  # Days for momentum calculation


def get_robust_atm_iv(tq, current_price, target_date_str):
    """Get robust ATM IV for a given expiration, avoiding bad near-zero IV data."""
    try:
        chain = tq.option_chain(target_date_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        
        df['volume'] = df['volume'].fillna(0)
        df['openInterest'] = df['openInterest'].fillna(0)
        
        df = df[
            ((df['volume'] > 50) | (df['openInterest'] > 500)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.05) &  # Filter out near-zero IV
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()
        
        if len(df) < 10:
            return None
        
        # Robust ATM IV: median of strikes within ±2% moneyness with reasonable IV
        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02)]
        
        if len(atm_candidates) >= 3:
            return atm_candidates['impliedVolatility'].median()
        else:
            valid_strikes = df[df['impliedVolatility'] > 0.05]
            if len(valid_strikes) == 0:
                return None
            atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
            return valid_strikes.loc[atm_idx, 'impliedVolatility']
    except Exception:
        return None


def get_nearest_liquid_expiration(tq, max_dte=45):
    """Get the nearest liquid expiration (DTE 7-45 days)."""
    try:
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 7 <= dte <= max_dte:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        return valid_exps[0][0].strftime("%Y-%m-%d") if valid_exps else None
    except Exception:
        return None


def load_history():
    """Load IV history from JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_history(history):
    """Save IV history to JSON file."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def update_history(ticker, atm_iv, current_price, expiration):
    """Update history with today's ATM IV."""
    history = load_history()
    today = datetime.now().strftime("%Y-%m-%d")
    
    if ticker not in history:
        history[ticker] = []
    
    # Add today's data
    history[ticker].append({
        'date': today,
        'atm_iv': float(atm_iv),
        'current_price': float(current_price),
        'expiration': expiration,
    })
    
    # Keep last 60 days
    history[ticker] = history[ticker][-60:]
    
    save_history(history)


def compute_momentum(history, ticker, lookback=LOOKBACK_DAYS):
    """Compute IV momentum (change over lookback period)."""
    if ticker not in history or len(history[ticker]) < lookback + 1:
        return np.nan
    
    recent = history[ticker][-(lookback + 1):]
    iv_now = recent[-1]['atm_iv']
    iv_past = recent[0]['atm_iv']
    
    if iv_past == 0:
        return np.nan
    
    # Return absolute change and percent change
    abs_change = iv_now - iv_past
    pct_change = abs_change / iv_past
    
    return {
        'abs_change': abs_change,
        'pct_change': pct_change,
        'iv_now': iv_now,
        'iv_past': iv_past,
    }


def compute_iv_momentum_signal(ticker_str):
    """Compute IV momentum signal for a single ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Get nearest liquid expiration
        exp_str = get_nearest_liquid_expiration(tq)
        if exp_str is None:
            return None
        
        # Get robust ATM IV
        atm_iv = get_robust_atm_iv(tq, current_price, exp_str)
        if atm_iv is None:
            return None
        
        # Update history
        update_history(ticker_str, atm_iv, current_price, exp_str)
        
        # Compute momentum
        momentum = compute_momentum(load_history(), ticker_str)
        if isinstance(momentum, float) and np.isnan(momentum):
            return {
                'ticker': ticker_str,
                'current_price': round(current_price, 2),
                'atm_iv': round(atm_iv, 4),
                'expiration': exp_str,
                'momentum_abs': np.nan,
                'momentum_pct': np.nan,
                'iv_now': round(atm_iv, 4),
                'iv_past': np.nan,
                'history_days': len(load_history().get(ticker_str, [])),
            }
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'atm_iv': round(atm_iv, 4),
            'expiration': exp_str,
            'momentum_abs': round(momentum['abs_change'], 4),
            'momentum_pct': round(momentum['pct_change'], 4),
            'iv_now': round(momentum['iv_now'], 4),
            'iv_past': round(momentum['iv_past'], 4),
            'history_days': len(load_history().get(ticker_str, [])),
        }
    
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📈 IV Momentum Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_iv_momentum_signal(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        print(f"\n{r['ticker']} (${r['current_price']}, exp: {r['expiration']}):")
        print(f"  ATM IV (now):     {r['atm_iv']:.4f}")
        if not np.isnan(r.get('momentum_pct', np.nan)):
            print(f"  IV {LOOKBACK_DAYS}d change:   {r['momentum_abs']:+.4f} ({r['momentum_pct']:+.2%})")
            print(f"  IV {LOOKBACK_DAYS}d ago:      {r['iv_past']:.4f}")
        else:
            print(f"  Momentum:         Building history ({r['history_days']} days)")
        print(f"  History length:   {r['history_days']} days")
    
    # Save latest snapshot
    os.makedirs("data", exist_ok=True)
    df = pd.DataFrame(results)
    path = "data/iv_momentum_latest.csv"
    df.to_csv(path, index=False)
    print(f"\n✅ Saved latest to {path}")
    print(f"   History saved to {HISTORY_FILE}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")