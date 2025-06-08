import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, time

# Page Configuration
st.set_page_config(page_title="Algo Trade Suite", layout="wide")
st.title("🧠 Algo Trading Strategy Dashboard")

# Sidebar - Strategy Builder
st.sidebar.header("📐 Strategy Builder")
symbol = st.sidebar.text_input("Stock Symbol (e.g., RELIANCE.NS)", "RELIANCE.NS")
start_date = st.sidebar.date_input("Start Date", datetime(2023, 1, 1))
end_date = st.sidebar.date_input("End Date", datetime.now())
interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "1d"], index=1)

strategy_type = st.sidebar.radio("Strategy Type", ["SMA Crossover", "RSI", "Breakout"])

# Custom Strategy Parameters
if strategy_type == "SMA Crossover":
    fast = st.sidebar.slider("Fast SMA", 5, 50, 10)
    slow = st.sidebar.slider("Slow SMA", 10, 200, 30)
elif strategy_type == "RSI":
    rsi_period = st.sidebar.slider("RSI Period", 5, 30, 14)
    rsi_overbought = st.sidebar.slider("Overbought Level", 60, 90, 70)
    rsi_oversold = st.sidebar.slider("Oversold Level", 10, 40, 30)
elif strategy_type == "Breakout":
    range_period = st.sidebar.slider("Range Lookback Period", 5, 60, 20)

# Fetch Data
data = yf.download(symbol, start=start_date, end=end_date, interval=interval)

if data.empty:
    st.error("No data found for selected symbol and time range.")
    st.stop()

# Strategy Logic
def apply_strategy(df):
    df = df.copy()
    df['Signal'] = ''

    if strategy_type == "SMA Crossover":
        df['SMA_Fast'] = df['Close'].rolling(window=fast).mean()
        df['SMA_Slow'] = df['Close'].rolling(window=slow).mean()
        df['Signal'] = np.where(df['SMA_Fast'] > df['SMA_Slow'], 'BUY', 'SELL')

    elif strategy_type == "RSI":
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=rsi_period).mean()
        avg_loss = loss.rolling(window=rsi_period).mean()
        rs = avg_gain / avg_loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['Signal'] = np.where(df['RSI'] < rsi_oversold, 'BUY',
                                np.where(df['RSI'] > rsi_overbought, 'SELL', ''))

    elif strategy_type == "Breakout":
        df['High_Max'] = df['High'].rolling(window=range_period).max()
        df['Low_Min'] = df['Low'].rolling(window=range_period).min()
        df['Signal'] = np.where(df['Close'] > df['High_Max'].shift(1), 'BUY',
                                np.where(df['Close'] < df['Low_Min'].shift(1), 'SELL', ''))
    return df

data = apply_strategy(data)

# Backtest Results
def backtest(df):
    df = df.copy()
    df['Position'] = df['Signal'].replace({'BUY': 1, 'SELL': -1}).ffill().fillna(0)
    df['Return'] = df['Close'].pct_change()
    df['Strategy_Return'] = df['Position'].shift(1) * df['Return']
    df['Equity_Curve'] = (1 + df['Strategy_Return']).cumprod()
    return df

data = backtest(data)

# Display Strategy Table
st.subheader(f"Strategy Output: {symbol}")
st.dataframe(data.tail(20))

# Plot
fig = go.Figure()
fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Close'))
if 'SMA_Fast' in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA_Fast'], name='Fast SMA'))
if 'SMA_Slow' in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA_Slow'], name='Slow SMA'))
if 'Equity_Curve' in data.columns:
    fig.add_trace(go.Scatter(x=data.index, y=data['Equity_Curve'], name='Equity Curve', yaxis='y2'))
fig.update_layout(title="Price and Strategy Performance",
                  yaxis=dict(title='Price'),
                  yaxis2=dict(title='Equity Curve', overlaying='y', side='right'))
st.plotly_chart(fig, use_container_width=True)

# Strategy Performance Summary
total_return = data['Equity_Curve'].iloc[-1] - 1
max_drawdown = ((data['Equity_Curve'].cummax() - data['Equity_Curve']) / data['Equity_Curve'].cummax()).max()
sharpe_ratio = data['Strategy_Return'].mean() / data['Strategy_Return'].std() * np.sqrt(252 if interval == '1d' else 78)

st.metric("Total Return", f"{total_return:.2%}")
st.metric("Max Drawdown", f"{max_drawdown:.2%}")
st.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")

st.info("✅ This dashboard supports live data testing, backtesting, and basic strategy building. To connect to real-time broker APIs (Zerodha, Fyers), backend integration is needed.")
