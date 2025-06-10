import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config("📈 200MA + 44MA Crossover Strategy", layout="wide")
st.title("📈 200 MA + 44 MA Crossover Strategy Dashboard")

# Sidebar
symbol = st.sidebar.text_input("Enter NSE Symbol (e.g. RELIANCE.NS)", value="RELIANCE.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2025-06-10"))
show_signals = st.sidebar.checkbox("✅ Show Crossover Signal Dates")

# Data Fetch
@st.cache_data
def get_data(symbol, start, end):
    data = yf.download(symbol, start=start, end=end)
    data.dropna(inplace=True)
    return data

df = get_data(symbol, start_date, end_date)

# Compute MAs
df['MA44'] = df['Close'].rolling(window=44).mean()
df['MA200'] = df['Close'].rolling(window=200).mean()

# Generate Signal
df['Signal'] = 0
df.loc[df['MA44'] > df['MA200'], 'Signal'] = 1
df.loc[df['MA44'] < df['MA200'], 'Signal'] = -1
df['Crossover'] = df['Signal'].diff()

# Determine Trend and Signal
last_signal = df['Signal'].iloc[-1]
if last_signal == 1:
    trend_text = "📈 Bullish (MA44 > MA200)"
    signal_text = "✅ BUY"
elif last_signal == -1:
    trend_text = "📉 Bearish (MA44 < MA200)"
    signal_text = "🚫 SELL"
else:
    trend_text = "🔁 Neutral / No Clear Trend"
    signal_text = "⏳ WAIT"

# Candlestick + MA Chart
fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df['MA44'], mode='lines', name='44 MA', line=dict(color='blue')))
fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], mode='lines', name='200 MA', line=dict(color='orange')))
fig.update_layout(title=f"{symbol} - 44MA vs 200MA", xaxis_title='Date', yaxis_title='Price', height=500)

# Optional Signal Points
if show_signals:
    buy_signals = df[df['Crossover'] == 2]
    sell_signals = df[df['Crossover'] == -2]
    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Close'], mode='markers', name='BUY Signal',
                             marker=dict(color='green', size=8, symbol='arrow-up')))
    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['Close'], mode='markers', name='SELL Signal',
                             marker=dict(color='red', size=8, symbol='arrow-down')))

st.plotly_chart(fig, use_container_width=True)

# Display Metrics
col1, col2, col3 = st.columns(3)

try:
    last_close = float(df['Close'].iloc[-1])
    col1.metric("Last Close", f"₹{last_close:.2f}")
except:
    col1.metric("Last Close", "N/A")

col2.metric("Trend", trend_text)
col3.metric("Signal", signal_text)
