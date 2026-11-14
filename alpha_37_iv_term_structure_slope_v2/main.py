"""
Compute IV Term Structure Slope alpha signal for a watchlist of tickers.

IV Term Structure Slope measures the change in ATM implied volatility
across different expiration dates. A positive slope indicates that near-term
IV is higher than longer-dated IV, suggesting a bullish view on near-term
volatility and potential mean reversion.
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


def compute_iv_term_structure_slope(ticker_str):
    """Compute IV term structure slope for a single ticker.
    
    The slope is calculated as the linear regression slope of ATM IV
    across expiration dates. Positive slope = near-term IV > long-term IV
    (bullish for near-term volatility).
    """
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
            except (ValueError, TypeError):
                continue
        valid_exps.sort()
        
        if not valid_exps:
            return None
        
        # Get ATM IV for each expiration
        iv_series = []
        for exp in valid_exps:
            try:
                chain = tq.option_chain(exp.strftime("%Y-%m-%d"))
                iv = chain.impliedVolatility.iloc[-1]  # latest IV for that expiration
                iv_series.append(iv)
            except Exception:
                iv_series.append(np.nan)
        
        iv_series = pd.Series(iv_series)
        
        # Compute slope: linear regression of IV vs days to expiration
        # Days to expiration: (expiration date - current date) in days
        days_to_exp = [(e - now).days for e in valid_exps]
        
        # Remove any NaN values
        valid_idx = iv_series.notna()
        if valid_idx.sum() < 2:
            return None
        
        # Linear regression: slope = delta_IV / delta_days
        x = days_to_exp[valid_idx]
        y = iv_series[valid_idx]
        
        # Simple linear regression using numpy
        if len(x) > 1:
            slope = np.polyfit(x, y, 1)[0]
            intercept = np.polyfit(x, y, 1)[1]
            
            # Return slope and intercept
            return {
                'ticker': ticker_str,
                'current_price': round(current_price, 2),
                'atm_iv': round(iv_series.iloc[-1], 4),
                'term_structure_slope': round(slope, 4),
                'term_structure_intercept': round(intercept, 4),
                'n_expirations': len(valid_exps),
                'days_to_exp': x.tolist(),
            }
        return None
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {e}")
        return None


def main():
    """Compute IV Term Structure Slope for all tickers in the universe."""
    print(f"🔍 IV Term Structure Slope Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for ticker in TICKERS:
        result = compute_iv_term_structure_slope(ticker)
        if result:
            results.append(result)
    
    if not results:
        print("❌ No signals generated")
        return
    
    # Sort by slope (most positive first = strongest bullish signal)
    results.sort(key=lambda x: x['term_structure_slope'], reverse=True)
    
    print(f"\n📊 IV Term Structure Slope — {len(results)} tickers analyzed")
    print("\nTicker | Current Price | ATM IV | Term Structure Slope | N Expirations")
    print("-" * 80)
    
    for r in results:
        print(f"{r['ticker']:12} | {r['current_price']:>12} | {r['atm_iv']:>12} | {r['term_structure_slope']:>14} | {r['n_expirations']:>12}")
    
    print("\n💡 Interpretation:")
    print("   slope > 0 → Near-term IV > long-term IV (bullish on near-term volatility)")
    print("   slope < 0 → Long-term IV > near-term IV (bearish on near-term volatility)")
    print("   slope ≈ 0 → IV is flat across expirations (no term structure signal)")
    
    # Save to data/iv_term_structure_slope_latest.csv
    df = pd.DataFrame(results)
    df.to_csv('data/iv_term_structure_slope_latest.csv', index=False)
    print("\n✅ Saved to data/iv_term_structure_slope_latest.csv")
    print(f"   Total tickers: {len(results)}")


if __name__ == "__main__":
    main()
