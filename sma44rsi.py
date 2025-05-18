import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# === RSI Function ===
def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# === Signal Function ===
def generate_signals(data):
    data['MA44'] = data['Close'].rolling(window=44).mean()
    data['RSI'] = calculate_rsi(data)
    data['Signal'] = ''

    for i in range(1, len(data)):
        current_close = data['Close'].iloc[i]
        prev_close = data['Close'].iloc[i - 1]
        current_ma = data['MA44'].iloc[i]
        prev_ma = data['MA44'].iloc[i - 1]
        current_rsi = data['RSI'].iloc[i]

        if current_close > current_ma and current_rsi > 50 and prev_close <= prev_ma:
            data.at[data.index[i], 'Signal'] = 'Buy'
        elif current_close < current_ma and current_rsi < 50 and prev_close >= prev_ma:
            data.at[data.index[i], 'Signal'] = 'Sell'

    return data


# === Streamlit UI ===
st.title("📈 MA44 + RSI Swing Trade Strategy")

symbol = st.text_input("Enter stock symbol (e.g. INFY.NS, TCS.BO, RELIANCE.NS)", "RELIANCE.NS")
start = st.date_input("Start Date", pd.to_datetime("2023-01-01"))
end = st.date_input("End Date", pd.to_datetime("today"))

interval = st.selectbox("Select interval", ["1d", "1h", "30m", "15m"], index=0)

if st.button("Run Strategy"):
    try:
        df = yf.download(symbol, start=start, end=end, interval=interval)
        if df.empty or 'Close' not in df.columns:
            st.error("No data or missing 'Close' column. Please check symbol or try again later.")
        else:
            df = generate_signals(df)

            # Plot chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close'))
            fig.add_trace(go.Scatter(x=df.index, y=df['MA44'], mode='lines', name='MA44'))

            # Buy signals
            buys = df[df['Signal'] == 'Buy']
            fig.add_trace(go.Scatter(x=buys.index, y=buys['Close'], mode='markers', name='Buy',
                                     marker=dict(color='green', size=10, symbol='triangle-up')))

            # Sell signals
            sells = df[df['Signal'] == 'Sell']
            fig.add_trace(go.Scatter(x=sells.index, y=sells['Close'], mode='markers', name='Sell',
                                     marker=dict(color='red', size=10, symbol='triangle-down')))

            st.plotly_chart(fig, use_container_width=True)

            # RSI chart
            st.subheader("📉 RSI Indicator")
            st.line_chart(df[['RSI']])

            # Signal Table
            st.subheader("📋 Trade Signals")
            st.write(df[df['Signal'] != ''][['Close', 'MA44', 'RSI', 'Signal']])
    except Exception as e:
        st.error(f"Error: {e}")
