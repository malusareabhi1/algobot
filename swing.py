# Install dependencies
# pip install yfinance pandas ta streamlit

import yfinance as yf
import pandas as pd
import ta

def screen_stocks(stock_list):
    results = []

    for symbol in stock_list:
        try:
            df = yf.download(symbol + ".NS", period="3mo", interval="1d")
            df.dropna(inplace=True)

            df['sma_44'] = ta.trend.sma_indicator(df['Close'], window=44)
            df['volume_avg10'] = df['Volume'].rolling(10).mean()

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            if latest['Close'] > latest['sma_44'] and prev['Close'] < prev['sma_44']:
                if latest['Volume'] > latest['volume_avg10']:
                    results.append({
                        'Symbol': symbol,
                        'Close': latest['Close'],
                        'SMA44': latest['sma_44'],
                        'Volume': latest['Volume'],
                        'VolumeAvg10': latest['volume_avg10']
                    })
        except:
            continue

    return pd.DataFrame(results)
