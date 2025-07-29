import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("📈 RSI + EMA Crossover Strategy")

# Sidebar Inputs
st.sidebar.header("Strategy Settings")
ticker = st.sidebar.text_input("Enter Stock Symbol (NSE)", value="TATAPOWER.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))
interval = st.sidebar.selectbox("Timeframe", ["1d", "1h", "15m", "5m"], index=3)

# Fetch Data
df = yf.download(ticker, start=start_date, end=end_date, interval=interval)
df.dropna(inplace=True)

# Ensure 'Close' is clean
df = df[df['Close'].notnull()].copy()

# Calculate Indicators
df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()

try:
    rsi_calc = RSIIndicator(close=df['Close'], window=14)
    df['RSI'] = rsi_calc.rsi()
except Exception as e:
    st.error(f"RSI calculation error: {e}")
    st.stop()

# Signal Logic
df['Buy_Signal'] = (
    (df['EMA7'] > df['EMA21']) &
    (df['EMA7'].shift(1) <= df['EMA21'].shift(1)) &  # fresh crossover
    (df['RSI'] > 60) &
    (df['RSI'].shift(1) <= 60)  # fresh RSI cross
)

# Plot Chart
st.subheader(f"{ticker} - EMA Crossover + RSI > 60 Strategy")

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(df.index, df['Close'], label='Close', color='gray', alpha=0.6)
ax.plot(df.index, df['EMA7'], label='EMA 7', color='orange')
ax.plot(df.index, df['EMA21'], label='EMA 21', color='blue')

# Mark Buy Signals
buy_signals = df[df['Buy_Signal']]
ax.scatter(buy_signals.index, buy_signals['Close'], label='BUY', color='green', marker='^', s=100)

ax.set_title("Price Chart with Buy Signals")
ax.set_ylabel("Price")
ax.legend()

st.pyplot(fig)

# Show Dataframe
st.subheader("Buy Signal Log")
st.dataframe(buy_signals[['Close', 'EMA7', 'EMA21', 'RSI']].style.format({"Close": "{:.2f}", "RSI": "{:.2f}"}))
