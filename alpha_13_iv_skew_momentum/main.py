#!/usr/bin/env python3
"""IV Skew Momentum alpha signal.

Tracks the rate of change of put-call IV skew (25-delta) over time.
Signal = skew momentum (recent change in skew) vs. forward returns.
Hypothesis: Rapid skew steepening signals rising fear/hedging demand → subsequent
mean-reversion or directional move. Rapid skew flattening signals complacency.
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
import json

from common.universe import TICKERS
HISTORY_FILE = "data/iv_skew_momentum_history.json"
LOOKBACK_DAYS = 20  # Days of history to compute momentum


def get_25d_iv(chain_df, current_price, option_type='put'):
    """Approximate 25-delta IV by moneyness proxy.
    
    For puts: 25-delta ≈ strike ~ 0.95 * spot (OTM)
    For calls: 25-delta ≈ strike ~ 1.05 * spot (OTM)
    """
    if option_type == 'put':
        target_strike = current_price * 0.95
        candidates = chain_df[chain_df['strike'] < current_price]
    else:
        target_strike = current_price * 1.05
        candidates = chain_df[chain_df['strike'] > current_price]
    
    if len(candidates) == 0:
        return np.nan
    
    idx = (candidates['strike'] - target_strike).abs().idxmin()
    row = candidates.loc[idx]
    return row['impliedVolatility'] if pd.notna(row['impliedVolatility']) else np.nan


def compute_current_skew(ticker_str):
    """Compute current 25-delta put-call skew for a ticker."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Use nearest liquid expiration (7-45 DTE)
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 7 <= dte <= 45:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            return None
        
        # Nearest valid expiration with enough liquid strikes (thin ETF weeklies
        # such as GDX can fail the filter, so fall through to the next expiry)
        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
        
            chain = tq.option_chain(exp_str)
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
                continue
        
            put_25d = get_25d_iv(puts, current_price, 'put')
            call_25d = get_25d_iv(calls, current_price, 'call')
        
            if pd.notna(put_25d) and pd.notna(call_25d):
                break
        else:
            return None
        
        skew = put_25d - call_25d  # Positive = put premium (fear)
        
        return {
            'ticker': ticker_str,
            'date': datetime.now().strftime("%Y-%m-%d"),
            'current_price': round(current_price, 2),
            'expiration': exp_str,
            'dte': dte,
            'put_25d_iv': put_25d,
            'call_25d_iv': call_25d,
            'skew_25d': skew,
        }
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


def load_history():
    """Load skew history from JSON file."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_history(history):
    """Save skew history to JSON file."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)


def compute_skew_momentum(history, ticker, lookback=5):
    """Compute skew momentum (rate of change) for a ticker.
    
    Returns:
        dict with momentum metrics or None if insufficient history
    """
    if ticker not in history or len(history[ticker]) < lookback + 1:
        return None
    
    # Get recent skew values (sorted by date)
    records = sorted(history[ticker], key=lambda x: x['date'])
    recent = records[-(lookback + 1):]  # +1 for current
    
    if len(recent) < 2:
        return None
    
    skews = [r['skew_25d'] for r in recent]
    dates = [r['date'] for r in recent]
    
    # Simple momentum: (current - N_days_ago) / N_days
    current_skew = skews[-1]
    past_skew = skews[0]
    momentum = (current_skew - past_skew) / lookback
    
    # Also compute 5-day and 10-day momentum if available
    mom_5d = (skews[-1] - skews[-6]) / 5 if len(skews) >= 6 else np.nan
    mom_10d = (skews[-1] - skews[-11]) / 10 if len(skews) >= 11 else np.nan
    
    # Volatility of skew (regime indicator)
    skew_vol = np.std(skews) if len(skews) >= 3 else np.nan
    
    # Z-score of current skew vs recent history
    skew_mean = np.mean(skews[:-1])
    skew_std = np.std(skews[:-1])
    skew_zscore = (current_skew - skew_mean) / skew_std if skew_std > 0 else 0
    
    return {
        'ticker': ticker,
        'date': dates[-1],
        'current_skew': current_skew,
        'momentum_lookback': momentum,
        'momentum_5d': mom_5d,
        'momentum_10d': mom_10d,
        'skew_volatility': skew_vol,
        'skew_zscore': skew_zscore,
        'lookback_days': lookback,
        'n_obs': len(skews),
    }


def update_history_and_compute():
    """Main function: fetch current skew, update history, compute momentum."""
    print(f"\n📊 IV Skew Momentum Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load existing history
    history = load_history()
    
    # Fetch current skew for all tickers
    current_data = []
    for t in TICKERS:
        result = compute_current_skew(t)
        if result:
            current_data.append(result)
            # Update history
            if t not in history:
                history[t] = []
            # Avoid duplicate dates
            today = result['date']
            history[t] = [r for r in history[t] if r['date'] != today]
            history[t].append({
                'date': result['date'],
                'skew_25d': result['skew_25d'],
                'put_25d_iv': result['put_25d_iv'],
                'call_25d_iv': result['call_25d_iv'],
                'dte': result['dte'],
                'expiration': result['expiration'],
            })
            # Keep only last LOOKBACK_DAYS + buffer
            history[t] = sorted(history[t], key=lambda x: x['date'])[-(LOOKBACK_DAYS + 10):]
    
    if not current_data:
        print("No data collected.")
        return
    
    # Save updated history
    save_history(history)
    
    # Compute momentum for each ticker
    momentum_results = []
    for t in TICKERS:
        mom = compute_skew_momentum(history, t, lookback=5)
        if mom:
            momentum_results.append(mom)
    
    # Print current skew
    print("\n📈 Current 25-Delta Skew (Put IV - Call IV):")
    for r in current_data:
        print(f"  {r['ticker']} (${r['current_price']}, {r['dte']}d): "
              f"Put={r['put_25d_iv']:.4f} Call={r['call_25d_iv']:.4f} "
              f"Skew={r['skew_25d']:.4f}")
    
    # Print momentum
    print("\n⚡ Skew Momentum (5-day rate of change):")
    for m in momentum_results:
        mom_5d = m['momentum_5d']
        mom_str = f"{mom_5d:.6f}" if not pd.isna(mom_5d) else "N/A"
        z_str = f"{m['skew_zscore']:.2f}" if not pd.isna(m['skew_zscore']) else "N/A"
        vol_str = f"{m['skew_volatility']:.6f}" if not pd.isna(m['skew_volatility']) else "N/A"
        print(f"  {m['ticker']}: 5d_mom={mom_str}  z-score={z_str}  skew_vol={vol_str}")
    
    # Interpretation
    print("\n💡 Interpretation:")
    print("   momentum > 0 → Skew steepening (rising fear/put demand)")
    print("   momentum < 0 → Skew flattening (complacency/call demand)")
    print("   |z-score| > 2 → Skew at extreme vs recent history")
    print("   High skew_vol → Unstable regime, less reliable momentum")
    
    # Save latest snapshot
    os.makedirs("data", exist_ok=True)
    
    # Current skew snapshot
    skew_df = pd.DataFrame(current_data)
    skew_df.to_csv("data/iv_skew_momentum_latest.csv", index=False)
    
    # Momentum snapshot
    if momentum_results:
        mom_df = pd.DataFrame(momentum_results)
        mom_df.to_csv("data/iv_skew_momentum_signal_latest.csv", index=False)
        print(f"\n✅ Saved skew data to data/iv_skew_momentum_latest.csv")
        print(f"✅ Saved momentum signals to data/iv_skew_momentum_signal_latest.csv")
    else:
        print(f"\n✅ Saved skew data to data/iv_skew_momentum_latest.csv")
        print("   (Insufficient history for momentum signals yet)")
    
    print(f"   Total cost: ~$0.10-0.30 per run\n")


if __name__ == "__main__":
    update_history_and_compute()