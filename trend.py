import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import ta

# --- PAGE SETTINGS ---
st.set_page_config(page_title="📊 Stock Trend Analyzer", layout="wide")
st.title("📈 Multi-Timeframe Stock Analyzer with Pattern Detection")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Settings")
stock = st.sidebar.text_input("Enter Stock Symbol (e.g., TCS.NS)", "RELIANCE.NS")
timeframe = st.sidebar.selectbox("Select Timeframe", ["Daily", "Weekly", "Monthly"])
period = st.sidebar.selectbox("Select Lookback Period", ["1mo", "3mo", "6mo", "1y", "2y"])

# --- HELPER FUNCTION ---
def load_data(symbol, period, interval):
    try:
        df = yf.download(symbol, period=period, interval=interval)
        df.dropna(inplace=True)
        return df
    except:
        return pd.DataFrame()

# --- GET INTERVAL BASED ON TIMEFRAME ---
interval_map = {"Daily": "1d", "Weekly": "1wk", "Monthly": "1mo"}
interval = interval_map[timeframe]
df = load_data(stock, period, interval)

if df.empty:
    st.warning("⚠️ Could not load stock data. Please check the symbol and try again.")
    st.stop()

# --- TECHNICAL INDICATORS ---
df['SMA20'] = df['Close'].rolling(window=20).mean()
df['SMA50'] = df['Close'].rolling(window=50).mean()
df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
df['Trend'] = ['Bullish' if sma20 > sma50 else 'Bearish' for sma20, sma50 in zip(df['SMA20'], df['SMA50'])]

# --- CHART ---
st.subheader(f"{stock} - {timeframe} Chart with Trend and Indicators")
fig = go.Figure()
fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='Price'))
fig.add_trace(go.Scatter(x=df.index, y=df['SMA20'], mode='lines', name='SMA 20'))
fig.add_trace(go.Scatter(x=df.index, y=df['SMA50'], mode='lines', name='SMA 50'))
fig.update_layout(xaxis_rangeslider_visible=False)
st.plotly_chart(fig, use_container_width=True)

# --- TREND SUMMARY ---
st.subheader("📊 Trend Analysis")
latest = df.iloc[-1]
st.write(f"**Latest Close:** ₹{latest['Close']:.2f}")
st.write(f"**RSI:** {latest['RSI']:.2f} ({'Overbought' if latest['RSI'] > 70 else 'Oversold' if latest['RSI'] < 30 else 'Neutral'})")
st.write(f"**Trend (SMA20 vs SMA50):** {latest['Trend']}")

# --- PATTERN RECOGNITION (SIMPLE) ---
def detect_patterns(df):
    patterns = []
    if df['Close'].iloc[-1] > df['SMA20'].iloc[-1] > df['SMA50'].iloc[-1]:
        patterns.append("Strong Uptrend")
    if df['RSI'].iloc[-1] > 70:
        patterns.append("Overbought")
    elif df['RSI'].iloc[-1] < 30:
        patterns.append("Oversold")
    return patterns

patterns = detect_patterns(df)
st.subheader("🔍 Detected Patterns")
if patterns:
    for p in patterns:
        st.success(f"✅ {p}")
else:
    st.info("No clear patterns detected.")

# --- STRATEGY SUGGESTION ---
st.subheader("💡 Trading Suggestion")
if latest['Trend'] == 'Bullish' and latest['RSI'] < 70:
    st.success("📈 Suggestion: Consider Buying on Pullback")
elif latest['Trend'] == 'Bearish' and latest['RSI'] > 30:
    st.error("📉 Suggestion: Avoid or Look for Short Opportunities")
else:
    st.info("⚖️ Suggestion: Wait and Watch")
