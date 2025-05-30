import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.title("Swing Trading Dashboard")

# Sidebar Inputs
symbol = st.sidebar.text_input('Stock Symbol', 'AAPL')
start_date = st.sidebar.date_input('Start Date', pd.to_datetime('2023-01-01'))
end_date = st.sidebar.date_input('End Date', pd.to_datetime('today'))
ema_short = st.sidebar.slider('Short EMA Period', 10, 50, 21)
ema_long = st.sidebar.slider('Long EMA Period', 50, 200, 100)

# Data Fetch
@st.cache_data
def load_data(symbol, start, end):
    return yf.download(symbol, start=start, end=end)

data = load_data(symbol, start_date, end_date)
if data.empty:
    st.error("No data found for this symbol and date range.")
    st.stop()

# Indicator Calculation
data['EMA_short'] = data['Close'].ewm(span=ema_short).mean()
data['EMA_long'] = data['Close'].ewm(span=ema_long).mean()

# Generate Trade Signals (simple EMA crossover)
data['Signal'] = 0
data.loc[data['EMA_short'] > data['EMA_long'], 'Signal'] = 1  # Buy
data.loc[data['EMA_short'] < data['EMA_long'], 'Signal'] = -1 # Sell
data['Trade'] = data['Signal'].diff()

# Trade Log Creation
trades = []
position = 0
entry_price = 0
for i, row in data.iterrows():
    if row['Trade'] == 1:  # Buy signal
        position = 1
        entry_price = row['Close']
        trades.append({'Date': i, 'Type': 'Buy', 'Price': row['Close']})
    elif row['Trade'] == -1 and position == 1:  # Sell signal
        position = 0
        trades.append({'Date': i, 'Type': 'Sell', 'Price': row['Close'], 'PnL': row['Close'] - entry_price})

trade_log = pd.DataFrame(trades)
if not trade_log.empty:
    trade_log['Date'] = pd.to_datetime(trade_log['Date'])

# P&L Curve
data['Position'] = data['Signal'].shift().fillna(0)
data['Daily_Return'] = data['Close'].pct_change().fillna(0)
data['Strategy_Return'] = data['Daily_Return'] * data['Position']
data['Cumulative_PnL'] = (1 + data['Strategy_Return']).cumprod() - 1

# Candlestick Chart with Trade Markers
fig = go.Figure(data=[go.Candlestick(
    x=data.index,
    open=data['Open'],
    high=data['High'],
    low=data['Low'],
    close=data['Close'],
    name='Candlestick'
)])
# Add Buy/Sell Markers
if not trade_log.empty:
    buys = trade_log[trade_log['Type'] == 'Buy']
    sells = trade_log[trade_log['Type'] == 'Sell']
    fig.add_trace(go.Scatter(
        x=buys['Date'], y=buys['Price'],
        mode='markers', marker=dict(symbol='triangle-up', color='green', size=12),
        name='Buy'
    ))
    fig.add_trace(go.Scatter(
        x=sells['Date'], y=sells['Price'],
        mode='markers', marker=dict(symbol='triangle-down', color='red', size=12),
        name='Sell'
    ))
fig.update_layout(title=f'{symbol} Candlestick Chart with Trades', xaxis_title='Date', yaxis_title='Price')

# P&L Curve Plot
pnl_fig = go.Figure()
pnl_fig.add_trace(go.Scatter(
    x=data.index, y=data['Cumulative_PnL'],
    mode='lines', name='Cumulative P&L'
))
pnl_fig.update_layout(title='Strategy Cumulative P&L', xaxis_title='Date', yaxis_title='Cumulative Return')

# Layout
st.header("Candlestick Chart")
st.plotly_chart(fig, use_container_width=True)

st.header("Trade Log")
if not trade_log.empty:
    st.dataframe(trade_log)
else:
    st.write("No trades generated.")

st.header("Cumulative P&L Curve")
st.plotly_chart(pnl_fig, use_container_width=True)
