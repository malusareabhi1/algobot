import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("📈 RSI > 60 + EMA 7/21 Crossover Strategy")

# Sidebar Inputs
st.sidebar.header("Strategy Settings")
#ticker = st.sidebar.text_input("Enter Stock Symbol (NSE)", value="TATAPOWER.NS")
nse_stocks = {
    "Reliance Industries": "RELIANCE.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Infosys": "INFY.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "State Bank of India": "SBIN.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Tata Power": "TATAPOWER.NS",
    "Adani Enterprises": "ADANIENT.NS",
    "Hindustan Unilever": "HINDUNILVR.NS"
}

ticker_name = st.sidebar.selectbox("Select Stock", options=list(nse_stocks.keys()), index=7)
ticker = nse_stocks[ticker_name]

start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))
interval = st.sidebar.selectbox("Timeframe", ["1d", "1h", "15m", "5m"], index=3)

# Fetch data
df = yf.download(ticker, start=start_date, end=end_date, interval=interval)

# Validate Data
if df.empty or 'Close' not in df.columns:
    st.error("⚠️ No data fetched. Please check the symbol, date range, or interval.")
    st.stop()

# Clean Close column to ensure it's 1D Series
df = df.copy()
if isinstance(df['Close'].values[0], np.ndarray):  # Defensive check
    df['Close'] = df['Close'].apply(lambda x: float(x[0]) if isinstance(x, (np.ndarray, list)) else x)
else:
    df['Close'] = df['Close'].astype(float)

# Indicators
df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()

# RSI with guaranteed 1D input
try:
    rsi_series = RSIIndicator(close=pd.Series(df['Close'].values.flatten()), window=14).rsi()
    df['RSI'] = rsi_series.values
except Exception as e:
    st.error(f"⚠️ RSI calculation failed: {e}")
    st.stop()

# Signal Conditions
df['EMA_Cross'] = (df['EMA7'] > df['EMA21']) & (df['EMA7'].shift(1) <= df['EMA21'].shift(1))
df['RSI_Cross'] = (df['RSI'] > 60) & (df['RSI'].shift(1) <= 60)
df['Buy_Signal'] = df['EMA_Cross'] & df['RSI_Cross']

buy_signals = df[df['Buy_Signal']].copy()

# Plotting
st.subheader(f"📊 {ticker} - Price Chart")

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(df.index, df['Close'], label='Close Price', color='gray')
ax.plot(df.index, df['EMA7'], label='EMA 7', color='orange')
ax.plot(df.index, df['EMA21'], label='EMA 21', color='blue')
ax.scatter(buy_signals.index, buy_signals['Close'], color='green', label='BUY Signal', marker='^', s=100)
ax.set_title("Price with BUY Signals")
ax.legend()
st.pyplot(fig)

# RSI Chart
st.subheader("📉 RSI Chart")
fig2, ax2 = plt.subplots(figsize=(14, 3))
ax2.plot(df.index, df['RSI'], label='RSI', color='purple')
ax2.axhline(60, color='red', linestyle='--', label='RSI 60')
ax2.set_ylim(0, 100)
ax2.legend()
st.pyplot(fig2)

# Buy Signal Table
st.subheader("✅ Buy Signal Log")
st.dataframe(buy_signals[['Close', 'EMA7', 'EMA21', 'RSI']].style.format({"Close": "{:.2f}", "RSI": "{:.2f}"}))
