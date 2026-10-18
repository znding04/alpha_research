#!/usr/bin/env python3
"""Information Coefficient analysis for VRP Skew signal.

Tests cross-sectional predictive power of VRP skew on forward returns.
"""
import os
import sys
sys.path.insert(0, "/Users/znding04/Work/alpha_research")

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from common.utils import compute_ic, rolling_ic, compute_signal_metrics, half_life_of_mean_reversion

TICKERS = ["AAPL", "SPY", "QQQ", "MSFT", "GOOGL", "AMZN"]


def get_realized_vol(ticker_str, lookback_days=30):
    """Compute realized volatility from daily close prices."""
    try:
        tq = yf.Ticker(ticker_str)
        hist = tq.history(period=f"{lookback_days + 5}d", interval="1d")
        if len(hist) < lookback_days:
            return np.nan
        closes = hist['Close'].dropna()
        log_returns = np.log(closes / closes.shift(1)).dropna()
        rv = log_returns.std() * np.sqrt(252)
        return float(rv)
    except Exception:
        return np.nan


def get_otm_iv(chain_df, current_price, option_type, moneyness_target=0.05):
    """Get IV for OTM option at target moneyness."""
    if option_type == 'put':
        target_strike = current_price * (1 - moneyness_target)
        candidates = chain_df[(chain_df['strike'] < current_price) & 
                              (chain_df['impliedVolatility'].notna()) &
                              (chain_df['impliedVolatility'] > 0.01) &
                              (chain_df['lastPrice'] > 0)]
    else:
        target_strike = current_price * (1 + moneyness_target)
        candidates = chain_df[(chain_df['strike'] > current_price) & 
                              (chain_df['impliedVolatility'].notna()) &
                              (chain_df['impliedVolatility'] > 0.01) &
                              (chain_df['lastPrice'] > 0)]
    
    if len(candidates) == 0:
        return np.nan
    
    idx = (candidates['strike'] - target_strike).abs().idxmin()
    return candidates.loc[idx, 'impliedVolatility']


def compute_daily_vrp_skew(ticker_str, rv_lookback=30, moneyness=0.05, max_dte=45):
    """Compute VRP skew for a single ticker on a single day."""
    try:
        tq = yf.Ticker(ticker_str)
        info = tq.info
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if current_price is None or current_price <= 0:
            return None
        
        rv = get_realized_vol(ticker_str, rv_lookback)
        if pd.isna(rv):
            return None
        rv_sq = rv ** 2
        
        expirations = list(tq.options)
        now = datetime.now()
        valid_exps = []
        for e in expirations:
            try:
                d = datetime.strptime(e, "%Y-%m-%d")
                dte = (d - now).days
                if 2 < dte <= max_dte:
                    valid_exps.append((d, dte))
            except ValueError:
                continue
        valid_exps.sort(key=lambda x: x[0])
        
        if not valid_exps:
            return None
        
        vrp_skews = []
        for exp_date, dte in valid_exps:
            exp_str = exp_date.strftime("%Y-%m-%d")
            try:
                chain = tq.option_chain(exp_str)
                df = pd.concat([chain.calls, chain.puts], ignore_index=True)
                df['volume'] = df['volume'].fillna(0)
                df['openInterest'] = df['openInterest'].fillna(0)
                liquid = df[((df['volume'] > 10) | (df['openInterest'] > 100))].copy()
                
                if len(liquid) < 20:
                    continue
                
                put_iv = get_otm_iv(liquid, current_price, 'put', moneyness)
                call_iv = get_otm_iv(liquid, current_price, 'call', moneyness)
                
                if pd.isna(put_iv) or pd.isna(call_iv):
                    continue
                
                put_vrp = put_iv ** 2 - rv_sq
                call_vrp = call_iv ** 2 - rv_sq
                vrp_skew = put_vrp - call_vrp
                vrp_skews.append(vrp_skew)
            except Exception:
                continue
        
        if not vrp_skews:
            return None
        
        return np.nanmean(vrp_skews)
        
    except Exception:
        return None


def build_history(days=60):
    """Build historical VRP skew data by fetching daily snapshots.
    
    Note: yfinance only gives current option chain. For true historical
    backtesting, would need to store daily snapshots or use a data vendor.
    This is a placeholder that simulates history by re-running current values.
    """
    print(f"Building {days}-day history for VRP Skew...")
    print("WARNING: yfinance only provides current option chain.")
    print("For real backtesting, historical option data is required.")
    print("⚠️ SYNTHETIC — not evidence: today's signal is back-filled onto past dates (+ noise),")
    print("   which is look-ahead. Any IC below is a pipeline demo only.")
    
    # Create synthetic history from current values (for demo only)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    history = pd.DataFrame(index=dates)
    
    for t in TICKERS:
        current_skew = compute_daily_vrp_skew(t)
        if current_skew is not None:
            # Add some noise for demonstration
            history[t] = current_skew + np.random.normal(0, abs(current_skew) * 0.1, len(dates))
        else:
            history[t] = np.nan
    
    return history


def get_forward_returns(tickers, days=60, horizon=5):
    """Get forward returns for IC calculation."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + horizon + 10)
    
    returns_data = {}
    for t in tickers:
        try:
            tq = yf.Ticker(t)
            hist = tq.history(start=start_date.strftime("%Y-%m-%d"), 
                             end=end_date.strftime("%Y-%m-%d"), interval="1d")
            if len(hist) > horizon:
                closes = hist['Close']
                fwd_ret = closes.shift(-horizon) / closes - 1
                returns_data[t] = fwd_ret
        except Exception:
            continue
    
    return pd.DataFrame(returns_data).dropna(how='all')


if __name__ == "__main__":
    print(f"\n📊 VRP Skew IC Analysis — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)
    
    # Build signal history (placeholder - needs real historical data)
    signal_history = build_history(60)
    print(f"\nSignal history shape: {signal_history.shape}")
    print(f"Date range: {signal_history.index[0].date()} to {signal_history.index[-1].date()}")
    
    # Get forward returns
    returns_history = get_forward_returns(TICKERS, days=60, horizon=5)
    print(f"\nReturns history shape: {returns_history.shape}")
    
    # Align
    common_dates = signal_history.index.intersection(returns_history.index)
    if len(common_dates) < 10:
        print("\n⚠️ Insufficient overlapping data for IC analysis.")
        print("Need historical option data for proper backtest.")
        exit(0)
    
    sig_aligned = signal_history.loc[common_dates]
    ret_aligned = returns_history.loc[common_dates]
    
    # Stack to long format for cross-sectional IC
    sig_stacked = sig_aligned.stack()
    ret_stacked = ret_aligned.stack()
    common_idx = sig_stacked.index.intersection(ret_stacked.index)
    
    if len(common_idx) < 10:
        print("⚠️ Insufficient aligned observations.")
        exit(0)
    
    sig_final = sig_stacked.loc[common_idx]
    ret_final = ret_stacked.loc[common_idx]
    
    # Cross-sectional IC per date
    ic_by_date = []
    for date in sig_aligned.index:
        date_sig = sig_aligned.loc[date].dropna()
        date_ret = ret_aligned.loc[date].dropna()
        common = date_sig.index.intersection(date_ret.index)
        if len(common) >= 4:
            ic = date_sig.loc[common].rank().corr(date_ret.loc[common].rank())
            ic_by_date.append((date, ic))
    
    if not ic_by_date:
        print("⚠️ No valid IC observations.")
        exit(0)
    
    ic_series = pd.Series(dict(ic_by_date), name='ic')
    print(f"\n📈 IC Statistics — SYNTHETIC, not evidence ({len(ic_series)} observations):")
    print(f"  Mean IC:   {ic_series.mean():.4f}")
    print(f"  Std IC:    {ic_series.std():.4f}")
    print(f"  IR:        {ic_series.mean() / ic_series.std() if ic_series.std() > 0 else np.nan:.4f}")
    print(f"  Win Rate:  {(ic_series > 0).mean():.2%}")
    print(f"  Max IC:    {ic_series.max():.4f}")
    print(f"  Min IC:    {ic_series.min():.4f}")
    
    # Half-life
    hl = half_life_of_mean_reversion(ic_series)
    print(f"  Half-life: {hl:.1f} days" if not np.isnan(hl) else "  Half-life: N/A")
    
    # Rolling IC
    rolling = rolling_ic(sig_aligned.T, ret_aligned.T, window=20)
    print(f"\n📊 Rolling IC (20-day window): {rolling.dropna().shape[0]} windows")
    if len(rolling.dropna()) > 0:
        print(f"  Latest: {rolling.dropna().iloc[-1]:.4f}")
        print(f"  Mean:   {rolling.mean():.4f}")
    
    # Save IC series
    os.makedirs("data", exist_ok=True)
    ic_series.to_csv("data/vrp_skew_ic_history.csv")
    print(f"\n✅ IC history saved to data/vrp_skew_ic_history.csv")