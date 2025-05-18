import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# RSI calculation
def calculate_rsi(data, period=14):
    delta = data['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Signal generation
def generate_signals(data):
    data['MA44'] = data['Close'].rolling(window=44).mean()
    data['RSI'] = calculate_rsi(data)
    data['Signal'] = np.nan

    for i in range(1, len(data)):
        try:
            curr_close = data['Close'].iloc[i]
            prev_close = data['Close'].iloc[i - 1]
            curr_ma = data['MA44'].iloc[i]
            prev_ma = data['MA44'].iloc[i - 1]
            curr_rsi = data['RSI'].iloc[i]

            if pd.notna(curr_ma) and pd.notna(prev_ma) and pd.notna(curr_rsi):
                if (
                    curr_close > curr_ma and
                    curr_rsi > 50 and
                    prev_close <= prev_ma
                ):
                    data.at[data.index[i], 'Signal'] = 'Buy'

                elif (
                    curr_close < curr_ma and
                    curr_rsi < 50 and
                    prev_close >= prev_ma
                ):
                    data.at[data.index[i], 'Signal'] = 'Sell'
        except Exception as e:
            print(f"Error at index {i}: {e}")
    return data


# Streamlit UI
st.title("📊 MA44 + RSI Swing Trading Strategy")

symbol = st.text_input("Enter stock symbol (e.g., TATAPOWER.NS)", value="RELIANCE.NS")
start = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
end = st.date_input("End Date", value=pd.to_datetime("today"))
interval = st.selectbox("Interval", ["1d", "1h", "30m", "15m"], index=0)

if st.button("Run Strategy"):
    df = yf.download(symbol, start=start, end=end, interval=interval)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    if df.empty:
        st.error("No data found. Please check the stock symbol.")
    else:
        df = df.dropna()
        df = generate_signals(df)

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name='Close Price'))
        fig.add_trace(go.Scatter(x=df.index, y=df['MA44'], name='MA44'))

        buy_signals = df[df['Signal'] == 'Buy']
        sell_signals = df[df['Signal'] == 'Sell']

        fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'],
                                 mode='markers', name='Buy',
                                 marker=dict(color='green', symbol='triangle-up', size=10)))

        fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'],
                                 mode='markers', name='Sell',
                                 marker=dict(color='red', symbol='triangle-down', size=10)))

        st.plotly_chart(fig, use_container_width=True)

        # RSI Plot
        st.subheader("RSI")
        st.line_chart(df['RSI'])

        # Signal Table
        st.subheader("Signal Table")
        st.write(df)
        st.write(df[df['Signal'].notna()][['Close', 'MA44', 'RSI', 'Signal']])
