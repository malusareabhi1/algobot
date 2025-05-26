import streamlit as st
import yfinance as yf
import pandas as pd

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

            # Calculate SMA manually
            df['sma'] = df['Close'].rolling(window=sma_period).mean()

            # Calculate volume average manually
            df['volume_avg'] = df['Volume'].rolling(window=volume_lookback).mean()

            df = df.dropna()

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            if float(latest['Close']) > float(latest['sma']) and float(prev['Close']) < float(prev['sma']):
                if float(latest['Volume']) > float(latest['volume_avg']):
                    entry_price = round(float(latest['Close']), 2)
                    stop_loss = round(float(prev['Low']), 2)
                    risk = entry_price - stop_loss
                    target1 = round(entry_price + 1.5 * risk, 2)
                    target2 = round(entry_price + 2.5 * risk, 2)

                    results.append({
                        'Symbol': symbol,
                        'Close': entry_price,
                        f'SMA{sma_period}': round(float(latest['sma']), 2),
                        'Volume': int(latest['Volume']),
                        f'VolumeAvg{volume_lookback}': int(latest['volume_avg']),
                        'Entry': entry_price,
                        'Stop Loss': stop_loss,
                        'Target 1': target1,
                        'Target 2': target2
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
