import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="Smart Chart & Trend Scanner", layout="wide")

st.title("📊 Smart Stock Analyzer: Chart + Trend + Signal")

# Sidebar Inputs
symbol = st.sidebar.text_input("Enter Stock Ticker (e.g. RELIANCE.NS)", value="RELIANCE.NS")
interval_option = st.sidebar.selectbox("Timeframe", ["1d - Daily", "1wk - Weekly", "1mo - Monthly"])
period = st.sidebar.selectbox("Data Period", ["1mo", "3mo", "6mo", "1y", "2y"])

interval = interval_option.split(" - ")[0]

# Fetch Data
@st.cache_data
def get_data(symbol, interval, period):
    data = yf.download(symbol, interval=interval, period=period)
    data.dropna(inplace=True)
    return data

df = get_data(symbol, interval, period)

# Indicators (without ta)
def compute_indicators(df):
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA50'] = df['Close'].rolling(window=50).mean()
    delta = df['Close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=14).mean()
    avg_loss = pd.Series(loss).rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

df = compute_indicators(df)

# Trend Detection
def detect_trend(df):
    if df['MA20'].iloc[-1] > df['MA50'].iloc[-1]:
        return "📈 Uptrend"
    elif df['MA20'].iloc[-1] < df['MA50'].iloc[-1]:
        return "📉 Downtrend"
    else:
        return "🔁 Sideways"

trend = detect_trend(df)

# Signal Suggestion
def get_signal(df):
    last_rsi = df['RSI'].iloc[-1]
    if last_rsi < 30 and trend == "📈 Uptrend":
        return "✅ BUY (RSI Oversold + Uptrend)"
    elif last_rsi > 70 and trend == "📉 Downtrend":
        return "🔻 SELL (RSI Overbought + Downtrend)"
    else:
        return "⏳ HOLD / Wait"

signal = get_signal(df)

# Plot Chart
def plot_chart(df, title):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['Open'], high=df['High'],
                                 low=df['Low'], close=df['Close'],
                                 name="Candles"))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='blue', width=1), name="MA20"))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], line=dict(color='orange', width=1), name="MA50"))
    fig.update_layout(title=title, xaxis_rangeslider_visible=False, height=600)
    return fig

# Show Output
st.plotly_chart(plot_chart(df, f"{symbol} Candlestick Chart ({interval_option})"), use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Trend", trend)
col2.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
col3.metric("Signal", signal)

# Pattern Detection (very basic)
def detect_pattern(df):
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Hammer pattern (close > open, small body, long lower shadow)
    body = abs(latest['Close'] - latest['Open'])
    lower_shadow = latest['Open'] - latest['Low'] if latest['Close'] > latest['Open'] else latest['Close'] -_
