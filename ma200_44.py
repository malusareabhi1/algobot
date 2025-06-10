import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="📉 200MA + 44MA Crossover Strategy", layout="wide")

st.title("📈 200MA + 44MA Crossover Strategy")

# Sidebar Inputs
symbol = st.sidebar.text_input("Enter Stock Symbol (e.g. INFY.NS)", value="RELIANCE.NS")
period = st.sidebar.selectbox("Select Data Period", ["6mo", "1y", "2y", "5y"])
interval = st.sidebar.selectbox("Select Timeframe", ["1d", "1wk", "1mo"])

# Download data
@st.cache_data
def get_data(symbol, period, interval):
    df = yf.download(symbol, period=period, interval=interval)
    df.dropna(inplace=True)
    return df

df = get_data(symbol, period, interval)

# Compute Moving Averages
df['MA44'] = df['Close'].rolling(window=44).mean()
df['MA200'] = df['Close'].rolling(window=200).mean()

# Generate Buy/Sell Signals
df['Signal'] = 0
df['Signal'][44:] = np.where(df['MA44'][44:] > df['MA200'][44:], 1, 0)
df['Position'] = df['Signal'].diff()

# Plotting Chart
def plot_chart(df):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name="Candlestick"
    ))

    fig.add_trace(go.Scatter(x=df.index, y=df['MA44'], line=dict(color='blue', width=1), name="44MA"))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA200'], line=dict(color='orange', width=1), name="200MA"))

    # Buy Signals
    buy_signals = df[df['Position'] == 1]
    sell_signals = df[df['Position'] == -1]

    fig.add_trace(go.Scatter(
        x=buy_signals.index,
        y=buy_signals['Close'],
        mode='markers',
        marker=dict(symbol='triangle-up', color='green', size=10),
        name='Buy Signal'
    ))

    # Sell Signals
    fig.add_trace(go.Scatter(
        x=sell_signals.index,
        y=sell_signals['Close'],
        mode='markers',
        marker=dict(symbol='triangle-down', color='red', size=10),
        name='Sell Signal'
    ))

    fig.update_layout(title=f"{symbol} - 200MA & 44MA Crossover", xaxis_rangeslider_visible=False, height=600)
    return fig

st.plotly_chart(plot_chart(df), use_container_width=True)

# Summary
latest_signal = df['Position'].iloc[-1]
signal_text = "📉 SELL Signal" if latest_signal == -1 else "📈 BUY Signal" if latest_signal == 1 else "⏳ HOLD / NO Change"

col1, col2, col3 = st.columns(3)
col1.metric("Last Close", f"₹{df['Close'].iloc[-1]:.2f}")
col2.metric("Trend Signal", signal_text)
col3.metric("MA44 vs MA200", "Bullish" if df['MA44'].iloc[-1] > df['MA200'].iloc[-1] else "Bearish")
