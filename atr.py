import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# Strategy parameters
st.sidebar.header('Strategy Parameters')
symbol = st.sidebar.text_input('Stock Symbol', 'AAPL')
ema_short = st.sidebar.slider('Short EMA Period', 10, 50, 21)
ema_medium = st.sidebar.slider('Medium EMA Period', 30, 100, 50)
ema_long = st.sidebar.slider('Long EMA Period', 50, 200, 100)
atr_period = st.sidebar.slider('ATR Period', 5, 20, 14)

# Fetch data
@st.cache_data
def load_data(symbol):
    return yf.download(symbol, period='1y')

data = load_data(symbol)

if data.empty:
    st.error("No data found for this symbol")
else:
    # Calculate indicators
    data['EMA_short'] = data['Close'].ewm(span=ema_short).mean()
    data['EMA_medium'] = data['Close'].ewm(span=ema_medium).mean()
    data['EMA_long'] = data['Close'].ewm(span=ema_long).mean()
    
    # Calculate ATR
    high_low = data['High'] - data['Low']
    high_close = abs(data['High'] - data['Close'].shift())
    low_close = abs(data['Low'] - data['Close'].shift())
    data['TR'] = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    data['ATR'] = data['TR'].rolling(atr_period).mean()
    
    # Generate signals
    data['Signal'] = 0
    long_condition = (data['EMA_short'] > data['EMA_medium']) & \
                    (data['EMA_medium'] > data['EMA_long'])
    short_condition = (data['EMA_short'] < data['EMA_medium']) & \
                     (data['EMA_medium'] < data['EMA_long'])
    
    data.loc[long_condition, 'Signal'] = 1
    data.loc[short_condition, 'Signal'] = -1
    
    # Plotting
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=data.index,
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close'],
                    name='Price'))
    
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA_short'], 
                    line=dict(color='purple', width=2), 
                    name=f'EMA {ema_short}'))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA_medium'], 
                    line=dict(color='orange', width=2), 
                    name=f'EMA {ema_medium}'))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA_long'], 
                    line=dict(color='blue', width=2), 
                    name=f'EMA {ema_long}'))
    
    # Add signals
    buy_signals = data[data['Signal'] == 1]
    sell_signals = data[data['Signal'] == -1]
    
    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Low']*0.98,
                    mode='markers', marker=dict(color='green', size=10),
                    name='Buy Signal'))
    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['High']*1.02,
                    mode='markers', marker=dict(color='red', size=10),
                    name='Sell Signal'))
    
    fig.update_layout(title=f'{symbol} Swing Trading Signals',
                     xaxis_title='Date',
                     yaxis_title='Price',
                     showlegend=True)
    
    st.plotly_chart(fig)
    
    # Strategy statistics
    st.subheader('Strategy Details')
    col1, col2 = st.columns(2)
    with col1:
        st.metric('Current ATR', f"${data['ATR'].iloc[-1]:.2f}")
    with col2:
        st.metric('Last Signal', 
                 'Buy' if data['Signal'].iloc[-1] == 1 else 
                 'Sell' if data['Signal'].iloc[-1] == -1 else 'Neutral')
