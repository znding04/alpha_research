#!/usr/bin/env python3
"""IV Surface Curvature alpha signal.

Computes the curvature (convexity) of the implied volatility smile via
butterfly spreads (long call/put wings, short ATM body).
Signal = normalized smile curvature (vol of vol proxy) vs forward returns.

Positive curvature (smile) = demand for tail protection / jump risk premium.
Cross-sectionally: High curvature tickers → higher crash risk, potential
mean-reversion bounce or volatility expansion.
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


def fit_iv_smile(chain_df, current_price, option_type='call'):
    """
    Fit a quadratic IV smile: IV = a + b*m + c*m^2 where m = log(K/S).
    
    Returns:
        dict with 'a', 'b', 'c' (curvature), 'r2', 'n_points'
    """
    # Filter liquid options with valid IV
    df = chain_df.copy()
    df['volume'] = df['volume'].fillna(0).astype(int)
    df['openInterest'] = df['openInterest'].fillna(0).astype(int)
    
    liquid = df[
        (df['volume'] > 10) | (df['openInterest'] > 100)
    ].copy()
    liquid = liquid[
        (liquid['impliedVolatility'].notna()) &
        (liquid['impliedVolatility'] > 0.01) &
        (liquid['impliedVolatility'] < 3.0) &
        (liquid['lastPrice'] > 0)
    ].copy()
    
    if len(liquid) < 6:
        return None
    
    # Moneyness: log(K/S)
    liquid['moneyness'] = np.log(liquid['strike'] / current_price)
    liquid = liquid[liquid['moneyness'].abs() <= 0.3]  # Within ~30% moneyness
    
    if len(liquid) < 5:
        return None
    
    # Quadratic fit: IV = a + b*m + c*m^2
    m = liquid['moneyness'].values
    iv = liquid['impliedVolatility'].values
    
    # Weight by liquidity (volume + OI)
    weights = liquid['volume'].values + liquid['openInterest'].values
    weights = weights / weights.sum() if weights.sum() > 0 else np.ones_like(weights) / len(weights)
    
    # Weighted polynomial fit
    try:
        coeffs = np.polyfit(m, iv, 2, w=weights)
        # coeffs[0] = c (m^2 coefficient = curvature)
        # coeffs[1] = b (m coefficient = skew)
        # coeffs[2] = a (constant = ATM IV)
        a, b, c = coeffs[2], coeffs[1], coeffs[0]
        
        # R-squared
        iv_pred = np.polyval(coeffs, m)
        ss_res = np.sum(weights * (iv - iv_pred)**2)
        ss_tot = np.sum(weights * (iv - np.average(iv, weights=weights))**2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0
        
        return {
            'atm_iv': a,
            'skew': b,
            'curvature': c,
            'r2': r2,
            'n_points': len(liquid),
        }
    except Exception:
        return None


def compute_butterfly_metrics(ticker_str, max_dte=45):
    """
    Compute smile curvature using butterfly spreads.
    
    Butterfly = Call(K-dK) - 2*Call(K) + Call(K+dK)
    (or same for puts, or average)
    
    Normalized by ATM IV to get dimensionless curvature.
    """
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        
        if current_price is None or current_price <= 0:
            return None
        
        # Get expirations
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 7 <= dte <= max_dte:  # Skip very short DTE (< 1 week)
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            return None
        
        # Use nearest liquid expiration (typically 2-6 weeks)
        target_exp, dte = valid_exps[0]
        target_str = target_exp.strftime("%Y-%m-%d")
        
        chain = tq.option_chain(target_str)
        
        # Fit smiles for calls and puts separately
        call_fit = fit_iv_smile(chain.calls, current_price, 'call')
        put_fit = fit_iv_smile(chain.puts, current_price, 'put')
        
        if call_fit is None and put_fit is None:
            return None
        
        # Combine call and put curvature (average if both available)
        if call_fit and put_fit:
            curvature = (call_fit['curvature'] + put_fit['curvature']) / 2
            skew = (call_fit['skew'] + put_fit['skew']) / 2
            atm_iv = (call_fit['atm_iv'] + put_fit['atm_iv']) / 2
            r2 = (call_fit['r2'] + put_fit['r2']) / 2
            n_points = call_fit['n_points'] + put_fit['n_points']
        elif call_fit:
            curvature = call_fit['curvature']
            skew = call_fit['skew']
            atm_iv = call_fit['atm_iv']
            r2 = call_fit['r2']
            n_points = call_fit['n_points']
        else:
            curvature = put_fit['curvature']
            skew = put_fit['skew']
            atm_iv = put_fit['atm_iv']
            r2 = put_fit['r2']
            n_points = put_fit['n_points']
        
        # Normalize curvature by ATM IV (dimensionless, comparable across tickers)
        # Curvature has units of IV/moneyness^2, divide by ATM IV
        normalized_curvature = curvature / atm_iv if atm_iv > 0 else 0
        
        # Also compute explicit butterfly at ATM
        # Butterfly ≈ 0.5 * curvature * (dK)^2 where dK is strike spacing
        # In moneyness space: butterfly ≈ curvature * (Δm)^2
        # Typical Δm for 25-delta ≈ 0.15 (log(1.05) ≈ 0.05, log(0.95) ≈ -0.05)
        # So butterfly_25d ≈ curvature * 0.15^2 = curvature * 0.0225
        butterfly_25d = curvature * 0.0225
        
        return {
            'ticker': ticker_str,
            'current_price': round(current_price, 2),
            'dte': dte,
            'atm_iv': round(atm_iv, 4),
            'skew': round(skew, 4),
            'curvature': round(curvature, 6),
            'normalized_curvature': round(normalized_curvature, 6),
            'butterfly_25d': round(butterfly_25d, 6),
            'r2': round(r2, 4),
            'n_points': n_points,
            'call_fit': call_fit,
            'put_fit': put_fit,
        }
        
    except Exception as e:
        print(f"  ⚠️ {ticker_str}: {type(e).__name__}: {e}")
        return None


if __name__ == "__main__":
    print(f"\n📊 IV Surface Curvature Alpha Signal — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    results = []
    for t in TICKERS:
        r = compute_butterfly_metrics(t)
        if r:
            results.append(r)
    
    if not results:
        print("No data collected.")
        exit(1)
    
    # Print summary
    for r in results:
        curv_sign = "📈 High Curvature" if r['normalized_curvature'] > 0.1 else ("📉 Low Curvature" if r['normalized_curvature'] < 0.02 else "➖ Normal")
        print(f"\n{r['ticker']} (${r['current_price']}, {r['dte']} DTE):")
        print(f"  ATM IV:              {r['atm_iv']:.4f}")
        print(f"  Skew (linear):       {r['skew']:.4f}")
        print(f"  Curvature (raw):     {r['curvature']:.6f}")
        print(f"  Norm. Curvature:     {r['normalized_curvature']:.6f}  ({curv_sign})")
        print(f"  Butterfly (25d):     {r['butterfly_25d']:.6f}")
        print(f"  Fit R²:              {r['r2']:.4f}")
        print(f"  Points used:         {r['n_points']}")
    
    # Save
    os.makedirs("data", exist_ok=True)
    path = "data/iv_surface_curvature_latest.csv"
    
    # Flatten for CSV
    flat_rows = []
    for r in results:
        flat_rows.append({
            'ticker': r['ticker'],
            'current_price': r['current_price'],
            'dte': r['dte'],
            'atm_iv': r['atm_iv'],
            'skew': r['skew'],
            'curvature': r['curvature'],
            'normalized_curvature': r['normalized_curvature'],
            'butterfly_25d': r['butterfly_25d'],
            'r2': r['r2'],
            'n_points': r['n_points'],
        })
    
    df = pd.DataFrame(flat_rows)
    df.to_csv(path, index=False)
    print(f"\n✅ Saved to {path}")
    print(f"   Total cost: ~$0.10-0.30 per run\n")