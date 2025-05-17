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
# Fix for multi-level columns from yfinance
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.reset_index(inplace=True)
df.rename(columns={"index": "Datetime"}, inplace=True)  # if needed


#st.subheader("📊 Raw Data Preview")
#st.write(df.tail())  # Check the last rows
#st.write("Data Shape:", df.shape)


# --- Step 2: Indicator selection ---
st.sidebar.header("Select Indicators")
use_ema = st.sidebar.checkbox("EMA")
use_rsi = st.sidebar.checkbox("RSI")
use_bbands = st.sidebar.checkbox("Bollinger Bands")
use_macd = st.sidebar.checkbox("MACD")
use_supertrend = st.sidebar.checkbox("Supertrend")
use_atr = st.sidebar.checkbox("ATR")
use_adx = st.sidebar.checkbox("ADX")
use_volume = st.sidebar.checkbox("Volume")
st.sidebar.header("Risk Management")
use_risk = st.sidebar.checkbox("Enable SL/Target")
stop_loss = st.sidebar.number_input("Stop Loss (%)", min_value=0.5, max_value=20.0, value=2.0)
target = st.sidebar.number_input("Target (%)", min_value=0.5, max_value=20.0, value=4.0)


if use_macd:
    macd = ta.trend.macd_diff(df["Close"])
    df["MACD"] = macd

if use_supertrend:
    supertrend = ta.trend.stc(df["Close"])
    df["Supertrend"] = supertrend  # STC is a close alternative in `ta`

if use_atr:
    df["ATR"] = ta.volatility.AverageTrueRange(df["High"], df["Low"], df["Close"]).average_true_range()

if use_adx:
    df["ADX"] = ta.trend.adx(df["High"], df["Low"], df["Close"])

if use_volume:
    df["Volume_MA"] = df["Volume"].rolling(window=20).mean()

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
    "Close < BB_Low",
    "MACD > 0",
    "Supertrend Rising",
    "Volume > 20MA"
])

exit_condition = st.sidebar.selectbox("Sell When", [
    "Close < EMA",
    "RSI > 70",
    "Close > BB_High",
    "MACD < 0",
    "Supertrend Falling",
    "Volume < 20MA"
])

# --- Strategy Logic ---
df["Signal"] = 0

# Entry logic
if entry_condition == "MACD > 0" and "MACD" in df:
    df.loc[df["MACD"] > 0, "Signal"] = 1
elif entry_condition == "Supertrend Rising" and "Supertrend" in df:
    df.loc[df["Supertrend"] > df["Supertrend"].shift(1), "Signal"] = 1
elif entry_condition == "Volume > 20MA" and "Volume_MA" in df:
    df.loc[df["Volume"] > df["Volume_MA"], "Signal"] = 1

# Exit logic
if exit_condition == "MACD < 0" and "MACD" in df:
    df.loc[df["MACD"] < 0, "Signal"] = -1
elif exit_condition == "Supertrend Falling" and "Supertrend" in df:
    df.loc[df["Supertrend"] < df["Supertrend"].shift(1), "Signal"] = -1
elif exit_condition == "Volume < 20MA" and "Volume_MA" in df:
    df.loc[df["Volume"] < df["Volume_MA"], "Signal"] = -1

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

# --- Trade Log ---
st.subheader("📄 Trade Log")

trade_log = df[df["Signal"] != 0][["Datetime", "Close", "Signal"]].copy()
trade_log["Action"] = trade_log["Signal"].apply(lambda x: "Buy" if x == 1 else "Sell")
trade_log.rename(columns={"Datetime": "Time", "Close": "Price"}, inplace=True)
trade_log = trade_log[["Time", "Action", "Price"]]

st.dataframe(trade_log, use_container_width=True)

# --- Download Button ---
csv = trade_log.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Download Trade Log as CSV",
    data=csv,
    file_name=f"{symbol}_trade_log.csv",
    mime='text/csv'
)


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
