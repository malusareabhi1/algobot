import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import ta

st.title("RSI + Bollinger Bands Swing Trading Dashboard")

# Sidebar Inputs
symbol = st.sidebar.text_input('Stock Symbol', 'AAPL')
start_date = st.sidebar.date_input('Start Date', pd.to_datetime('2023-01-01'))
end_date = st.sidebar.date_input('End Date', pd.to_datetime('today'))
rsi_period = st.sidebar.slider('RSI Period', 5, 30, 14)
bb_period = st.sidebar.slider('Bollinger Bands Period', 10, 40, 20)
bb_std = st.sidebar.slider('Bollinger Bands Std Dev', 1, 4, 2)

# Data Fetch
@st.cache_data
def load_data(symbol, start, end):
    return yf.download(symbol, start=start, end=end)

data = load_data(symbol, start_date, end_date)
if data.empty:
    st.error("No data found for this symbol and date range.")
    st.stop()

# Indicator Calculation
data['RSI'] = ta.momentum.RSIIndicator(data['Close'], window=rsi_period).rsi()
bb = ta.volatility.BollingerBands(data['Close'], window=bb_period, window_dev=bb_std)
data['BB_upper'] = bb.bollinger_hband()
data['BB_lower'] = bb.bollinger_lband()
data['BB_mid'] = bb.bollinger_mavg()

# Signal Generation
data['Signal'] = 0

# Long Entry: RSI crosses above 30 and close < lower BB
long_entry = (
    (data['RSI'].shift(1) < 30) & (data['RSI'] >= 30) &
    (data['Close'] < data['BB_lower'])
)

# Short Entry: RSI crosses below 70 and close > upper BB
short_entry = (
    (data['RSI'].shift(1) > 70) & (data['RSI'] <= 70) &
    (data['Close'] > data['BB_upper'])
)

data.loc[long_entry, 'Signal'] = 1
data.loc[short_entry, 'Signal'] = -1

# Trade Log Creation
trades = []
position = 0
entry_price = 0
entry_date = None

for i, row in data.iterrows():
    if not pd.isna(row['Signal']):
        if row['Signal'] == 1 and position == 0:
            position = 1
            entry_price = row['Close']
            entry_date = i
            trades.append({'Date': i, 'Type': 'Buy', 'Price': row['Close']})
        elif row['Signal'] == -1 and position == 0:
            position = -1
            entry_price = row['Close']
            entry_date = i
            trades.append({'Date': i, 'Type': 'Sell', 'Price': row['Close']})
        # Exit long
        elif position == 1 and ((row['RSI'] > 60) or (row['Close'] > row['BB_mid'])):
            pnl = row['Close'] - entry_price
            trades.append({'Date': i, 'Type': 'Sell (Exit)', 'Price': row['Close'], 'PnL': pnl})
            position = 0
            entry_price = 0
            entry_date = None
        # Exit short
        elif position == -1 and ((row['RSI'] < 40) or (row['Close'] < row['BB_mid'])):
            pnl = entry_price - row['Close']
            trades.append({'Date': i, 'Type': 'Buy (Exit)', 'Price': row['Close'], 'PnL': pnl})
            position = 0
            entry_price = 0
            entry_date = None

trade_log = pd.DataFrame(trades)
if not trade_log.empty:
    trade_log['Date'] = pd.to_datetime(trade_log['Date'])

# P&L Curve
data['Position'] = 0
if not trade_log.empty:
    # Set position based on trade log
    for idx, trade in trade_log.iterrows():
        if trade['Type'] == 'Buy':
            data.loc[data.index >= trade['Date'], 'Position'] = 1
        elif trade['Type'] == 'Sell':
            data.loc[data.index >= trade['Date'], 'Position'] = -1
        elif trade['Type'] in ['Sell (Exit)', 'Buy (Exit)']:
            data.loc[data.index >= trade['Date'], 'Position'] = 0

data['Daily_Return'] = data['Close'].pct_change().fillna(0)
data['Strategy_Return'] = data['Daily_Return'] * data['Position'].shift().fillna(0)
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
# Add Bollinger Bands
fig.add_trace(go.Scatter(
    x=data.index, y=data['BB_upper'],
    line=dict(color='rgba(0,100,200,0.2)', width=1), name='BB Upper'
))
fig.add_trace(go.Scatter(
    x=data.index, y=data['BB_lower'],
    line=dict(color='rgba(0,100,200,0.2)', width=1), name='BB Lower'
))
fig.add_trace(go.Scatter(
    x=data.index, y=data['BB_mid'],
    line=dict(color='rgba(0,100,200,0.5)', width=1, dash='dot'), name='BB Mid'
))
# Add Buy/Sell Markers
if not trade_log.empty:
    buys = trade_log[trade_log['Type'].str.contains('Buy')]
    sells = trade_log[trade_log['Type'].str.contains('Sell')]
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
fig.update_layout(title=f'{symbol} Candlestick Chart with RSI + Bollinger Bands Signals', xaxis_title='Date', yaxis_title='Price')

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
