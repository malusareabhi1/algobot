import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import plotly.graph_objs as go
import time

st.set_page_config(layout="wide")
st.title("🧪 Custom Strategy Builder with Live Data")

# --- Step 1: Stock selection ---
symbol = st.selectbox("Select Symbol", ["RELIANCE.NS", "TCS.NS", "INFY.NS", "NIFTYBEES.NS"])
interval = st.selectbox("Interval", ["1d", "1h", "15m", "5m", "1m"])
start_date = st.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.date_input("End Date", pd.to_datetime("2024-12-31"))

# --- Live Data Mode ---
st.sidebar.header("📡 Live Data Settings")
live_mode = st.sidebar.checkbox("🔴 Enable Live Mode")
refresh_rate = st.sidebar.slider("⏱️ Refresh every (seconds)", 5, 60, 15)

# --- Load Data ---
@st.cache_data(ttl=60, show_spinner=False)
def load_data(symbol, start, end, interval):
    data = yf.download(symbol, start=start, end=end, interval=interval, progress=False)
    data.dropna(inplace=True)
    return data

if live_mode:
    df = yf.download(symbol, period="1d", interval="1m", progress=False)
    df.dropna(inplace=True)
else:
    df = load_data(symbol, start_date, end_date, interval)

# Fix columns if needed
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.reset_index(inplace=True)

# --- Indicators ---
st.sidebar.header("Select Indicators")
use_ema = st.sidebar.checkbox("EMA")
use_rsi = st.sidebar.checkbox("RSI")
use_bbands = st.sidebar.checkbox("Bollinger Bands")

if use_ema:
    ema_period = st.sidebar.slider("EMA Period", 5, 100, 20)
    df["EMA"] = ta.trend.ema_indicator(df['Close'], window=ema_period)

if use_rsi:
    rsi_period = st.sidebar.slider("RSI Period", 5, 30, 14)
    df["RSI"] = ta.momentum.RSIIndicator(df["Close"], window=rsi_period).rsi()

if use_bbands:
    bb_period = st.sidebar.slider("BB Period", 10, 30, 20)
    bb = ta.volatility.BollingerBands(df["Close"], window=bb_period)
    df["BB_High"] = bb.bollinger_hband()
    df["BB_Low"] = bb.bollinger_lband()

# --- Strategy Logic ---
st.sidebar.header("Set Entry/Exit Rules")
entry_condition = st.sidebar.selectbox("Buy When", ["Close > EMA", "RSI < 30", "Close < BB_Low"])
exit_condition = st.sidebar.selectbox("Sell When", ["Close < EMA", "RSI > 70", "Close > BB_High"])

df["Signal"] = 0
if entry_condition == "Close > EMA" and "EMA" in df:
    df.loc[df["Close"] > df["EMA"], "Signal"] = 1
elif entry_condition == "RSI < 30" and "RSI" in df:
    df.loc[df["RSI"] < 30, "Signal"] = 1
elif entry_condition == "Close < BB_Low" and "BB_Low" in df:
    df.loc[df["Close"] < df["BB_Low"], "Signal"] = 1

if exit_condition == "Close < EMA" and "EMA" in df:
    df.loc[df["Close"] < df["EMA"], "Signal"] = -1
elif exit_condition == "RSI > 70" and "RSI" in df:
    df.loc[df["RSI"] > 70, "Signal"] = -1
elif exit_condition == "Close > BB_High" and "BB_High" in df:
    df.loc[df["Close"] > df["BB_High"], "Signal"] = -1

# --- Chart ---
st.subheader("📈 Price Chart with Signals")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Candles'))

if "EMA" in df:
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA'], line=dict(color='orange'), name='EMA'))

buy_signals = df[df['Signal'] == 1]
sell_signals = df[df['Signal'] == -1]
fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='Buy', marker=dict(color='green', size=10)))
fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='Sell', marker=dict(color='red', size=10)))

fig.update_layout(height=600, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- Backtest Summary ---
st.subheader("🧮 Strategy Returns (Basic)")
df["Returns"] = df["Close"].pct_change()
df["Strategy"] = df["Signal"].shift(1) * df["Returns"]
cumulative_returns = (1 + df["Strategy"]).cumprod()
st.line_chart(cumulative_returns, use_container_width=True)

# --- Trade Log Download ---
st.subheader("📋 Trade Log")
try:
    trade_log = df[df["Signal"] != 0][["Datetime", "Close", "Signal"]].copy()
except:
    trade_log = df[df["Signal"] != 0][["Date", "Close", "Signal"]].copy()
trade_log["Action"] = trade_log["Signal"].map({1: "BUY", -1: "SELL"})

st.dataframe(trade_log)

csv = trade_log.to_csv(index=False).encode('utf-8')
st.download_button("⬇️ Download Trade Log CSV", data=csv, file_name=f"{symbol}_trade_log.csv", mime='text/csv')

# --- Live Refresh ---
if live_mode:
    st.success(f"Live Mode Active: Auto-refreshing every {refresh_rate} seconds.")
    time.sleep(refresh_rate)
    st.experimental_rerun()
