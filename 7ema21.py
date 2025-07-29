import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("📈 RSI + EMA Crossover Strategy (BUY Signal)")

# Sidebar Inputs
st.sidebar.header("Strategy Settings")
ticker = st.sidebar.text_input("Enter Stock Symbol (NSE)", value="TATAPOWER.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))
interval = st.sidebar.selectbox("Timeframe", ["1d", "1h", "15m", "5m"], index=3)

# Fetch Data
df = yf.download(ticker, start=start_date, end=end_date, interval=interval)

# Validate and Clean Data
if df.empty or 'Close' not in df.columns:
    st.error("⚠️ No data fetched. Please check the symbol, date range, or interval.")
    st.stop()

df = df[df['Close'].notnull()].copy()
df['Close'] = df['Close'].squeeze()  # Flatten to 1D

# Calculate Indicators
df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()

try:
    rsi_calc = RSIIndicator(close=df['Close'], window=14)
    df['RSI'] = rsi_calc.rsi()
except Exception as e:
    st.error(f"⚠️ RSI calculation failed: {e}")
    st.stop()

# Buy Signal Logic:
# 1. 7 EMA crosses above 21 EMA
# 2. RSI crosses above 60
df['EMA_Cross'] = (df['EMA7'] > df['EMA21']) & (df['EMA7'].shift(1) <= df['EMA21'].shift(1))
df['RSI_Cross'] = (df['RSI'] > 60) & (df['RSI'].shift(1) <= 60)
df['Buy_Signal'] = df['EMA_Cross'] & df['RSI_Cross']

# Show Buy Signals in Table
buy_signals = df[df['Buy_Signal']].copy()

# Plotting
st.subheader(f"📊 {ticker} - Strategy Chart")

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(df.index, df['Close'], label='Close Price', color='gray', alpha=0.5)
ax.plot(df.index, df['EMA7'], label='EMA 7', color='orange')
ax.plot(df.index, df['EMA21'], label='EMA 21', color='blue')

# Mark Buy Signals
ax.scatter(buy_signals.index, buy_signals['Close'], marker='^', color='green', s=100, label='BUY Signal')

ax.set_title("RSI + EMA Strategy (Buy Entries)")
ax.set_ylabel("Price")
ax.legend()
st.pyplot(fig)

# Show RSI Plot
st.subheader("📉 RSI Indicator")
fig2, ax2 = plt.subplots(figsize=(14, 3))
ax2.plot(df.index, df['RSI'], label='RSI', color='purple')
ax2.axhline(60, color='red', linestyle='--', label='RSI 60')
ax2.set_ylim(0, 100)
ax2.set_ylabel("RSI")
ax2.legend()
st.pyplot(fig2)

# Buy Signal Log Table
st.subheader("✅ Buy Signal Log")
st.dataframe(buy_signals[['Close', 'EMA7', 'EMA21', 'RSI']].style.format({"Close": "{:.2f}", "RSI": "{:.2f}"}))
