import streamlit as st
import pandas as pd
import yfinance as yf
import ta
import plotly.graph_objs as go

st.set_page_config(layout="wide")
st.title("🧪 Custom Strategy Builder")

# --- Step 1: Stock selection ---
symbol = st.selectbox("Select Symbol", ["RELIANCE.NS", "TCS.NS", "INFY.NS", "NIFTYBEES.NS"])
start_date = st.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.date_input("End Date", pd.to_datetime("2024-12-31"))
interval = st.selectbox("Interval", ["1d", "1h", "5m", "15m"])

# --- Load data ---
@st.cache_data
def load_data(symbol, start, end, interval):
    data = yf.download(symbol, start=start, end=end, interval=interval)
    data.dropna(inplace=True)
    return data

df = load_data(symbol, start_date, end_date, interval)

# --- Step 2: Indicator selection ---
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

# --- Step 3: Entry/Exit conditions (Basic logic for now) ---
st.sidebar.header("Set Entry/Exit Rules")

entry_condition = st.sidebar.selectbox("Buy When", [
    "Close > EMA",
    "RSI < 30",
    "Close < BB_Low"
])

exit_condition = st.sidebar.selectbox("Sell When", [
    "Close < EMA",
    "RSI > 70",
    "Close > BB_High"
])

# --- Strategy Logic ---
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

# --- Show data and signal chart ---
st.subheader("📈 Price Chart with Signals")

fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'], high=df['High'],
    low=df['Low'], close=df['Close'],
    name='Candles'
))

# Add EMA line
if "EMA" in df:
    fig.add_trace(go.Scatter(x=df.index, y=df['EMA'], line=dict(color='orange'), name='EMA'))

# Add signal markers
buy_signals = df[df['Signal'] == 1]
sell_signals = df[df['Signal'] == -1]
fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='Buy', marker=dict(color='green', size=10)))
fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='Sell', marker=dict(color='red', size=10)))

fig.update_layout(height=600, xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- Optional: Backtest Summary ---
st.subheader("🧮 Backtest Result (Basic)")
df["Returns"] = df["Close"].pct_change()
df["Strategy"] = df["Signal"].shift(1) * df["Returns"]
cumulative_returns = (1 + df["Strategy"]).cumprod()

st.line_chart(cumulative_returns, use_container_width=True)

#---

## 🚀 What You Can Build Next

#---- Add strategy saving/loading
#---- Multi-condition builder (e.g., EMA crossover + RSI)
#---- Add Telegram alerts
#---- Integrate with broker API for live trading
#---- Use advanced indicators (ATR, Supertrend, etc.)

#---

#---Would you like me to:
#---- Extend this with multi-condition logic?
#---- Add broker execution logic?
#---- Translate this to React + FastAPI format?

#---Let me know your next goal!
