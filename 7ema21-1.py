import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from ta.momentum import RSIIndicator

st.set_page_config(layout="wide")
st.title("📈 RSI > 60 + EMA 7/21 Crossover Strategy with Volume Confirmation")

# -----------------------------------------------
# Sidebar Inputs
st.sidebar.header("Strategy Settings")

nse_stocks = {
    "Adani Enterprises": "ADANIENT.NS",
    "Adani Ports": "ADANIPORTS.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "Axis Bank": "AXISBANK.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Bajaj Finserv": "BAJAJFINSV.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "Britannia Industries": "BRITANNIA.NS",
    "Cipla": "CIPLA.NS",
    "Coal India": "COALINDIA.NS",
    "Divi's Laboratories": "DIVISLAB.NS",
    "Dr. Reddy's Laboratories": "DRREDDY.NS",
    "Eicher Motors": "EICHERMOT.NS",
    "Grasim Industries": "GRASIM.NS",
    "HCL Technologies": "HCLTECH.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "HDFC Life Insurance": "HDFCLIFE.NS",
    "Hero MotoCorp": "HEROMOTOCO.NS",
    "Hindalco Industries": "HINDALCO.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "ITC": "ITC.NS",
    "Infosys": "INFY.NS",
    "JSW Steel": "JSWSTEEL.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "Larsen & Toubro": "LT.NS",
    "Mahindra & Mahindra": "M&M.NS",
    "Maruti Suzuki India": "MARUTI.NS",
    "Nestle India": "NESTLEIND.NS",
    "NTPC": "NTPC.NS",
    "Oil and Natural Gas Corporation": "ONGC.NS",
    "Power Grid Corporation": "POWERGRID.NS",
    "Reliance Industries": "RELIANCE.NS",
    "SBI Life Insurance": "SBILIFE.NS",
    "State Bank of India": "SBIN.NS",
    "Shree Cement": "SHREECEM.NS",
    "Sun Pharmaceutical": "SUNPHARMA.NS",
    "Tata Chemicals": "TATACHEM.NS",
    "Tata Consultancy Services": "TCS.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Tata Steel": "TATASTEEL.NS",
    "Tech Mahindra": "TECHM.NS",
    "Titan Company": "TITAN.NS",
    "UltraTech Cement": "ULTRACEMCO.NS",
    "UPL": "UPL.NS",
    "Wipro": "WIPRO.NS",
    "Zee Entertainment": "ZEEL.NS"
}

ticker_name = st.sidebar.selectbox("Select Stock", options=list(nse_stocks.keys()), index=30)
ticker = nse_stocks[ticker_name]

start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))
interval = st.sidebar.selectbox("Timeframe", ["1d", "1h", "15m", "5m"], index=0)

# -----------------------------------------------
# Fetch Data
df = yf.download(ticker, start=start_date, end=end_date, interval=interval)

# Validate Data
if df.empty or 'Close' not in df.columns:
    st.error("⚠️ No data fetched. Please check the symbol, date range, or interval.")
    st.stop()

df = df.copy()
df['Close'] = df['Close'].astype(float)

# -----------------------------------------------
# Indicators
df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
#df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()
try:
    close_series = pd.Series(df['Close'].values.flatten(), index=df.index)
    df['RSI'] = RSIIndicator(close=close_series, window=14).rsi()
except Exception as e:
    st.error(f"⚠️ RSI calculation failed: {e}")
    st.stop()


# Volume Confirmation
df['Avg_Volume'] = df['Volume'].rolling(window=20).mean()
df['Volume_Confirm'] = df['Volume'] > df['Avg_Volume']

# -----------------------------------------------
# BUY Signal Logic
df['EMA_Cross'] = (df['EMA7'] > df['EMA21']) & (df['EMA7'].shift(1) <= df['EMA21'].shift(1))
df['RSI_Cross'] = (df['RSI'] > 60) & (df['RSI'].shift(1) <= 60)
df['Buy_Signal'] = df['EMA_Cross'] & df['RSI_Cross'] & df['Volume_Confirm']

# SELL Signal Logic
df['EMA_Cross_Down'] = (df['EMA7'] < df['EMA21']) & (df['EMA7'].shift(1) >= df['EMA21'].shift(1))
df['RSI_Cross_Down'] = (df['RSI'] < 40) & (df['RSI'].shift(1) >= 40)
df['Sell_Signal'] = df['EMA_Cross_Down'] & df['RSI_Cross_Down'] & df['Volume_Confirm']

buy_signals = df[df['Buy_Signal']].copy()
sell_signals = df[df['Sell_Signal']].copy()

# -----------------------------------------------
# Stop Loss and Target Calculation
stop_loss_pct = 0.02
target_multiplier = 3

buy_signals['Stop_Loss'] = buy_signals['Close'] * (1 - stop_loss_pct)
buy_signals['Target'] = buy_signals['Close'] * (1 + stop_loss_pct * target_multiplier)

sell_signals['Stop_Loss'] = sell_signals['Close'] * (1 + stop_loss_pct)
sell_signals['Target'] = sell_signals['Close'] * (1 - stop_loss_pct * target_multiplier)

# -----------------------------------------------
# Plotting
st.subheader(f"📊 {ticker} - Price Chart")

fig, ax = plt.subplots(figsize=(14, 6))
ax.plot(df.index, df['Close'], label='Close Price', color='gray')
ax.plot(df.index, df['EMA7'], label='EMA 7', color='orange')
ax.plot(df.index, df['EMA21'], label='EMA 21', color='blue')
ax.scatter(buy_signals.index, buy_signals['Close'], color='green', label='BUY Signal', marker='^', s=100)
ax.scatter(sell_signals.index, sell_signals['Close'], color='red', label='SELL Signal', marker='v', s=100)
ax.set_title("Price with BUY/SELL Signals")
ax.legend()
st.pyplot(fig)

# RSI Chart
st.subheader("📉 RSI Chart")
fig2, ax2 = plt.subplots(figsize=(14, 3))
ax2.plot(df.index, df['RSI'], label='RSI', color='purple')
ax2.axhline(60, color='green', linestyle='--', label='RSI 60')
ax2.axhline(40, color='red', linestyle='--', label='RSI 40')
ax2.set_ylim(0, 100)
ax2.legend()
st.pyplot(fig2)

# -----------------------------------------------
# Signal Logs
st.subheader("✅ Buy Signal Log with Volume & Risk Levels")
st.dataframe(
    buy_signals[['Close', 'Stop_Loss', 'Target', 'EMA7', 'EMA21', 'RSI', 'Volume', 'Avg_Volume']]
    .style.format({"Close": "{:.2f}", "Stop_Loss": "{:.2f}", "Target": "{:.2f}", "RSI": "{:.2f}"})
)

st.subheader("🔻 Sell Signal Log with Volume & Risk Levels")
st.dataframe(
    sell_signals[['Close', 'Stop_Loss', 'Target', 'EMA7', 'EMA21', 'RSI', 'Volume', 'Avg_Volume']]
    .style.format({"Close": "{:.2f}", "Stop_Loss": "{:.2f}", "Target": "{:.2f}", "RSI": "{:.2f}"})
)

# -----------------------------------------------
# Strategy Description
st.markdown("""
### 📘 Strategy Logic

#### ✅ BUY Signal:
- EMA 7 crosses **above** EMA 21
- RSI crosses **above 60**
- Volume is **above 20-period average**

#### 🔻 SELL Signal:
- EMA 7 crosses **below** EMA 21
- RSI crosses **below 40**
- Volume is **above 20-period average**

#### 🔒 Risk Management:
- Stop Loss is set 2% below entry for BUY (above for SELL)
- Target is 3x the stop loss distance

---  
- Green arrows (↑) indicate BUY signals  
- Red arrows (↓) indicate SELL signals  
""")
