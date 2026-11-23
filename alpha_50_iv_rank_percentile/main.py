#!/usr/bin/env python3
"""Compute IV Rank Percentile (1-Year Snapshot History) alpha signal for 6 focus tickers.

This signal computes ATM IV from today's option chains, then ranks it against
1-year of accumulated daily option-chain snapshots stored in data/snapshots/.
If no historical snapshots exist, it defaults to 0.5 percentile (neutral).
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
from glob import glob

from common.universe import FOCUS_TICKERS

def compute_atm_iv(ticker_str):
    """Compute ATM IV for a single ticker from current option chains."""
    try:
        tq = yf.Ticker(ticker_str)
        # Get current price
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
            
        # Fetch option chains - take most liquid expiration
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                if d.date() > now.date() and (d - now).days <= 180:
                    valid_exps.append(d)
            except ValueError:
                continue
                
        if not valid_exps:
            return None
            
        # Use nearest meaningful expiration (skip DTE < 2)
        target_exp = min(
            [e for e in valid_exps if (e - now).days > 2],
            default=valid_exps[0]
        )
        target_str = target_exp.strftime("%Y-%m-%d")
        
        chain = tq.option_chain(target_str)
        df = pd.concat([chain.calls, chain.puts], ignore_index=True)
        
        # Fix dtypes: volume/OI are numpy int64, comparison fails on NaN/inf
        df['volume'] = df['volume'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        df['openInterest'] = df['openInterest'].fillna(0).replace([np.inf, -np.inf], 0).astype(int)
        
        # Filter: liquid + valid IV + positive price + reasonable IV
        df = df[
            ((df['volume'] > 10) | (df['openInterest'] > 100)) &
            (df['impliedVolatility'].notna()) &
            (df['impliedVolatility'] > 0.01) &
            (df['impliedVolatility'] < 3.0) &
            (df['lastPrice'] > 0)
        ].copy()
        
        if len(df) < 10:
            return None
            
        # Robust ATM IV: median of strikes within ±2% moneyness with IV > 5%
        moneyness = df['strike'] / current_price
        atm_candidates = df[(moneyness >= 0.98) & (moneyness <= 1.02) & (df['impliedVolatility'] > 0.05)]
        
        if len(atm_candidates) >= 3:
            atm_iv = atm_candidates['impliedVolatility'].median()
        else:
            # Fallback: single closest strike with IV > 0.05
            valid_strikes = df[df['impliedVolatility'] > 0.05]
            if len(valid_strikes) == 0:
                return None
            atm_idx = (valid_strikes['strike'] - current_price).abs().idxmin()
            atm_iv = valid_strikes.loc[atm_idx, 'impliedVolatility']
            
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'atm_iv': round(atm_iv, 4),
            'n_contracts': len(df),
        }
            
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None

def load_historical_atm_ivs():
    """Load ATM IV history from data/snapshots/ directory."""
    snapshot_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'snapshots')
    if not os.path.exists(snapshot_dir):
        print(f"  ⚠️ No snapshot directory found at {snapshot_dir}")
        return {}
    
    # Find all iv_rank_latest.csv files in snapshot subdirectories
    pattern = os.path.join(snapshot_dir, '*', 'iv_rank_latest.csv')
    snapshot_files = sorted(glob(pattern))
    
    if not snapshot_files:
        print(f"  ⚠️ No iv_rank_latest.csv files found in snapshots")
        return {}
    
    ticker_data = {t: {} for t in FOCUS_TICKERS}
    
    for f in snapshot_files:
        try:
            # Extract date from path: data/snapshots/YYYY-MM-DD/iv_rank_latest.csv
            date_str = os.path.basename(os.path.dirname(f))
            # Validate date format
            try:
                pd.Timestamp(date_str)
            except ValueError:
                continue
                
            df = pd.read_csv(f)
            if 'ticker' not in df.columns or 'atm_iv' not in df.columns:
                continue
                
            for _, row in df.iterrows():
                t = row['ticker']
                if t in ticker_data:
                    ticker_data[t][date_str] = row['atm_iv']
                    
        except Exception as e:
            print(f"  ⚠️ Failed to read {f}: {e}")
            continue
            
    # Convert to Series for each ticker
    result = {}
    for ticker, data in ticker_data.items():
        if data:
            s = pd.Series(data)
            s.index = pd.to_datetime(s.index)
            s = s.sort_index()
            result[ticker] = s
            
    return result

def compute_percentile_1y(current_atm_iv, historical_ivs):
    """Compute 1-year percentile rank of current ATM IV vs historical IVs."""
    if historical_ivs is None or len(historical_ivs) == 0:
        return 0.5
        
    # Use only last 365 days
    cutoff = historical_ivs.index.max() - pd.Timedelta(days=365)
    recent_ivs = historical_ivs[historical_ivs.index > cutoff]
    
    if len(recent_ivs) < 20:  # Need minimum history
        return 0.5
        
    min_iv = recent_ivs.min()
    max_iv = recent_ivs.max()
    
    if max_iv <= min_iv:
        return 0.5
        
    percentile = (current_atm_iv - min_iv) / (max_iv - min_iv)
    return float(np.clip(percentile, 0.0, 1.0))

if __name__ == "__main__":
    print(f"\\n🔍 IV Rank Percentile (1-Year Snapshot) — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Load historical ATM IVs from snapshots
    print("Loading historical ATM IVs from data/snapshots/...")
    historical_data = load_historical_atm_ivs()
    
    if historical_data:
        total_dates = sum(len(s) for s in historical_data.values())
        print(f"  Loaded {total_dates} historical ATM IV points across {len(historical_data)} tickers")
    else:
        print("  No historical data found - percentiles will default to 0.5")
    
    # Compute live ATM IVs and percentiles
    results = []
    
    for t in FOCUS_TICKERS:
        live = compute_atm_iv(t)
        if live:
            hist_ivs = historical_data.get(t)
            percentile = compute_percentile_1y(live['atm_iv'], hist_ivs)
            
            # Get latest snapshot date used for percentile
            if hist_ivs is not None and len(hist_ivs) > 0:
                cutoff = hist_ivs.index.max() - pd.Timedelta(days=365)
                recent = hist_ivs[hist_ivs.index > cutoff]
                pct_date = recent.index.max().strftime('%Y-%m-%d') if len(recent) > 0 else 'N/A'
            else:
                pct_date = 'N/A'
                
            live['iv_percentile_1y'] = round(percentile, 4)
            live['percentile_date'] = pct_date
            live['date'] = datetime.now().strftime('%Y-%m-%d')
            results.append(live)
            print(f"  {t}: ATM IV={live['atm_iv']:.4f}, 1Y Pctl={percentile:.4f} (n={live['n_contracts']})")
        else:
            print(f"  {t}: No data")
    
    if not results:
        print("No data collected.")
        exit(1)
        
    df = pd.DataFrame(results)
    cols = ['ticker', 'date', 'current_price', 'atm_iv', 'iv_percentile_1y', 'n_contracts', 'percentile_date']
    df = df[cols]
    
    print(f"\\n{'Ticker':<6} {'Price':>8} {'ATM IV':>8} {'Pctl 1Y':>8} {'Contracts':>10} {'Hist Date'}")
    print("-" * 65)
    for _, r in df.iterrows():
        print(f"{r['ticker']:<6} {r['current_price']:>8.2f} {r['atm_iv']:>8.4f} {r['iv_percentile_1y']:>8.4f} {r['n_contracts']:>10d} {r['percentile_date']}")
    
    print("\\n💡 Interpretation:")
    print("   iv_percentile_1y > 0.8 → IV expensive vs history (short vol / bearish)")
    print("   iv_percentile_1y < 0.2 → IV cheap vs history (long vol / bullish)")
    print("   0.2 ≤ pctl ≤ 0.8 → normal regime")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_rank_percentile_latest.csv"
    df = pd.DataFrame(results)
    df.to_csv(path, index=False)
    print(f"\\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run")