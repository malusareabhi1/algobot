import streamlit as st
import yfinance as yf
import pandas as pd
import ta

# Title
st.title("📈 Swing Trade Stock Screener (NIFTY 100)")

# Sidebar options
sma_period = st.sidebar.slider("SMA Period", min_value=20, max_value=100, value=44)
volume_lookback = st.sidebar.slider("Volume Avg Period", min_value=5, max_value=20, value=10)

# Sample NIFTY 100 stock list (shortened, you can replace with full list)
nifty_100 = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'LT', 'AXISBANK',
    'KOTAKBANK', 'HCLTECH', 'WIPRO', 'ITC', 'ULTRACEMCO', 'BAJFINANCE', 'ASIANPAINT'
]

# Multiselect
selected_stocks = st.multiselect("Select Stocks to Scan", nifty_100, default=nifty_100[:5])

@st.cache_data

def screen_stocks(stock_list, sma_period, volume_lookback):
    results = []

    for symbol in stock_list:
        try:
            df = yf.download(symbol + ".NS", period="6mo", interval="1d")
            df.dropna(inplace=True)

            df['sma'] = ta.trend.sma_indicator(close=df['Close'], window=sma_period).fillna(0)
            df['volume_avg'] = df['Volume'].rolling(volume_lookback).mean().fillna(0)

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            if latest['Close'] > latest['sma'] and prev['Close'] < prev['sma']:
                if latest['Volume'] > latest['volume_avg']:
                    results.append({
                        'Symbol': symbol,
                        'Close': round(latest['Close'], 2),
                        f'SMA{sma_period}': round(latest['sma'], 2),
                        'Volume': int(latest['Volume']),
                        f'VolumeAvg{volume_lookback}': int(latest['volume_avg'])
                    })
        except Exception as e:
            st.warning(f"Error loading {symbol}: {e}")
            continue

    return pd.DataFrame(results)

if st.button("🔍 Run Screener"):
    screener_result = screen_stocks(selected_stocks, sma_period, volume_lookback)
    if not screener_result.empty:
        st.success(f"Found {len(screener_result)} swing candidates")
        st.dataframe(screener_result)
        csv = screener_result.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "swing_candidates.csv", "text/csv")
    else:
        st.info("No stocks matched the criteria.")
