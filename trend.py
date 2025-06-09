import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="🚀 Advanced Stock Analyzer", layout="wide")

st.title("📊 Smart Stock Analyzer — Enhanced Edition")

# Sidebar Inputs
symbol = st.sidebar.text_input("Enter Stock Ticker (e.g. RELIANCE.NS)", value="RELIANCE.NS")
interval_option = st.sidebar.selectbox("Timeframe", ["1d - Daily", "1wk - Weekly", "1mo - Monthly"])
period = st.sidebar.selectbox("Data Period", ["1mo", "3mo", "6mo", "1y", "2y"])
interval = interval_option.split(" - ")[0]

# Data Fetcher
@st.cache_data
def get_data(symbol, interval, period):
    df = yf.download(symbol, interval=interval, period=period)
    df.dropna(inplace=True)
    return df

df = get_data(symbol, interval, period)

# Indicators Calculation
def compute_indicators(df):
    df['MA20'] = df['Close'].rolling(20).mean()
    df['MA50'] = df['Close'].rolling(50).mean()
    df['UpperBB'] = df['MA20'] + 2 * df['Close'].rolling(20).std()
    df['LowerBB'] = df['MA20'] - 2 * df['Close'].rolling(20).std()
    delta = df['Close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain, index=df.index).rolling(14).mean()
    avg_loss = pd.Series(loss, index=df.index).rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['Volatility'] = df['Close'].rolling(10).std()
    return df

df = compute_indicators(df)

# Trend & Signal
def detect_trend(df):
    if df['MA20'].iloc[-1] > df['MA50'].iloc[-1]:
        return "📈 Uptrend"
    elif df['MA20'].iloc[-1] < df['MA50'].iloc[-1]:
        return "📉 Downtrend"
    return "🔁 Sideways"

def get_signal(df, trend):
    last_rsi = df['RSI'].iloc[-1]
    if last_rsi < 30 and trend == "📈 Uptrend":
        return "✅ BUY (Oversold + Uptrend)"
    elif last_rsi > 70 and trend == "📉 Downtrend":
        return "🔻 SELL (Overbought + Downtrend)"
    return "⏳ HOLD / Wait"

trend = detect_trend(df)
signal = get_signal(df, trend)

# Pattern Detection
def detect_pattern(df):
    latest = df.iloc[-1]
    body = abs(latest['Close'] - latest['Open'])
    range_ = latest['High'] - latest['Low']
    lower_shadow = min(latest['Close'], latest['Open']) - latest['Low']
    upper_shadow = latest['High'] - max(latest['Close'], latest['Open'])

    if body / range_ < 0.3 and lower_shadow > body * 2:
        return "🔨 Hammer (Bullish)"
    elif body / range_ < 0.3 and upper_shadow > body * 2:
        return "⭐ Shooting Star (Bearish)"
    return "🔍 No strong pattern"

pattern = detect_pattern(df)

# Support & Resistance (basic)
def support_resistance(df):
    recent = df['Close'].tail(30)
    support = recent.min()
    resistance = recent.max()
    return round(support, 2), round(resistance, 2)

support, resistance = support_resistance(df)

# Chart Plot
def plot_chart(df, title):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'], name="Candles"))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], name='MA50', line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df.index, y=df['UpperBB'], name='Upper BB', line=dict(color='green', dash='dot')))
    fig.add_trace(go.Scatter(x=df.index, y=df['LowerBB'], name='Lower BB', line=dict(color='red', dash='dot')))
    fig.add_hline(y=support, line=dict(color="red", dash="dot"), annotation_text="Support")
    fig.add_hline(y=resistance, line=dict(color="green", dash="dot"), annotation_text="Resistance")
    fig.update_layout(title=title, xaxis_rangeslider_visible=False, height=600)
    return fig

# Volume Chart
def plot_volume(df):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color='purple'))
    fig.update_layout(title="Volume", height=250, xaxis_rangeslider_visible=False)
    return fig

# Layout
st.plotly_chart(plot_chart(df, f"{symbol} Chart ({interval_option})"), use_container_width=True)
st.plotly_chart(plot_volume(df), use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Trend", trend)
col2.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
col3.metric("Signal", signal)

col4, col5, col6 = st.columns(3)
col4.metric("Support", support)
col5.metric("Resistance", resistance)
col6.metric("Volatility (10)", f"{df['Volatility'].iloc[-1]:.2f}")

st.subheader("📐 Pattern Analysis")
st.info(pattern)

# News (optional with dummy text)
st.subheader("📰 News Headlines (Static Example)")
news_list = [
    f"{symbol}: Strong volumes suggest bullish interest.",
    f"{symbol}: Broker upgrades rating to 'Buy'.",
    f"{symbol}: RSI indicates possible reversal zone.",
]
for news in news_list:
    st.markdown(f"- {news}")
