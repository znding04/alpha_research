import yfinance as yf
import pandas as pd

tq = yf.Ticker('AAPL')
chain = tq.option_chain(list(tq.options)[0])
df = pd.concat([chain.calls, chain.puts], ignore_index=True)
print('dtypes:')
print(df.dtypes)
print()
print('Testing comparison...')
try:
    result = (df['volume'] > 50) | (df['openInterest'] > 500)
    print('Success:', result.head())
except Exception as e:
    print('Error:', type(e).__name__, e)

print()
print('Testing with .astype(int)...')
try:
    df2 = df.copy()
    df2['volume'] = df2['volume'].astype(int)
    df2['openInterest'] = df2['openInterest'].astype(int)
    result = (df2['volume'] > 50) | (df2['openInterest'] > 500)
    print('Success:', result.head())
except Exception as e:
    print('Error:', type(e).__name__, e)