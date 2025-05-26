import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# App configuration
st.set_page_config(page_title="Swing Trade Strategy", layout="wide")

# Sidebar inputs
st.sidebar.header("Strategy Parameters")
symbol = st.sidebar.text_input("Stock Symbol", "AAPL")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))
fast_ma = st.sidebar.slider("Fast MA Period", 10, 50, 20)
slow_ma = st.sidebar.slider("Slow MA Period", 30, 100, 50)
stop_loss = st.sidebar.number_input("Stop Loss (%)", 2.0, 10.0, 5.0)
take_profit = st.sidebar.number_input("Take Profit (%)", 2.0, 15.0, 8.0)

def calculate_signals(data):
    # Calculate moving averages
    data['Fast_MA'] = data['Close'].ewm(span=fast_ma, adjust=False).mean()
    data['Slow_MA'] = data['Close'].ewm(span=slow_ma, adjust=False).mean()
    
    # Generate signals
    data['Signal'] = 0
    data['Signal'] = np.where(
        (data['Fast_MA'] > data['Slow_MA']) & 
        (data['Fast_MA'].shift(1) <= data['Slow_MA'].shift(1)), 1, 0)
    data['Signal'] = np.where(
        (data['Fast_MA'] < data['Slow_MA']) & 
        (data['Fast_MA'].shift(1) >= data['Slow_MA'].shift(1)), -1, data['Signal'])
    
    return data

def plot_strategy(data):
    fig = go.Figure()
    
    # Price and MAs
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='Price'))
    fig.add_trace(go.Scatter(x=data.index, y=data['Fast_MA'], name=f'EMA {fast_ma}'))
    fig.add_trace(go.Scatter(x=data.index, y=data['Slow_MA'], name=f'EMA {slow_ma}'))
    
    # Buy signals
    buys = data[data['Signal'] == 1]
    fig.add_trace(go.Scatter(
        x=buys.index, y=buys['Low']*0.98, 
        mode='markers', name='Buy', marker=dict(color='green', size=10)))
    
    # Sell signals
    sells = data[data['Signal'] == -1]
    fig.add_trace(go.Scatter(
        x=sells.index, y=sells['High']*1.02, 
        mode='markers', name='Sell', marker=dict(color='red', size=10)))
    
    fig.update_layout(
        title=f'{symbol} Swing Trading Strategy',
        xaxis_title='Date',
        yaxis_title='Price',
        hovermode='x unified',
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

def calculate_trades(data):
    trades = []
    position = None
    
    for index, row in data.iterrows():
        if row['Signal'] == 1 and not position:
            entry_price = row['Close']
            stop_price = entry_price * (1 - stop_loss/100)
            target_price = entry_price * (1 + take_profit/100)
            position = {
                'Entry Date': index,
                'Entry Price': entry_price,
                'Stop Loss': stop_price,
                'Take Profit': target_price
            }
        elif row['Signal'] == -1 and position:
            exit_price = row['Close']
            position.update({
                'Exit Date': index,
                'Exit Price': exit_price,
                'P/L (%)': ((exit_price - position['Entry Price'])/position['Entry Price'])*100
            })
            trades.append(position)
            position = None
            
    return pd.DataFrame(trades)

# Main app
st.title("Swing Trading Strategy Analyzer")

# Load data
data = yf.download(symbol, start=start_date, end=end_date)
if data.empty:
    st.error("No data found for this symbol!")
else:
    data = calculate_signals(data)
    
    # Display charts
    plot_strategy(data)
    
    # Show trade history
    st.subheader("Trade History")
    trades_df = calculate_trades(data)
    
    if not trades_df.empty:
        st.dataframe(trades_df.style.format({
            'Entry Price': '{:.2f}',
            'Exit Price': '{:.2f}',
            'P/L (%)': '{:.2f}%'
        }), use_container_width=True)
        
        # Performance metrics
        total_return = trades_df['P/L (%)'].sum()
        win_rate = (trades_df['P/L (%)'] > 0).mean() * 100
        st.metric("Total Return", f"{total_return:.2f}%")
        st.metric("Win Rate", f"{win_rate:.2f}%")
    else:
        st.write("No trades generated in selected period")

# How to run
st.markdown("""
**How to Use:**
1. Install requirements: `pip install streamlit yfinance pandas plotly numpy`
2. Save as `swing_trader.py`
3. Run: `streamlit run swing_trader.py`
""")
