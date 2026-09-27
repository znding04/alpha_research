import yfinance as yf
import pandas as pd

tq = yf.Ticker('AAPL')
chain = tq.option_chain(list(tq.options)[0])
df = pd.concat([chain.calls, chain.puts], ignore_index=True)

print('Testing full filter...')
try:
    filtered = df[
        ((df['volume'] > 50) | (df['openInterest'] > 500)) &
        (df['impliedVolatility'].notna()) &
        (df['impliedVolatility'] > 0) &
        (df['impliedVolatility'] < 3.0) &
        (df['lastPrice'] > 0)
    ].copy()
    print('Success! Filtered shape:', filtered.shape)
    print(filtered.head())
except Exception as e:
    print('Error:', type(e).__name__, e)
    import traceback
    traceback.print_exc()