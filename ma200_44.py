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
# ------------------- BACKTEST MODULE -------------------
st.subheader("📊 Strategy Backtest Summary")

# Prepare signal dataframe
trades = []
position = None
entry_price = 0

for i in range(1, len(df)):
    if df['Crossover'].iloc[i] == 2:  # BUY
        if position is None:
            entry_price = df['Close'].iloc[i]
            entry_date = df.index[i]
            position = 'LONG'
    elif df['Crossover'].iloc[i] == -2:  # SELL
        if position == 'LONG':
            exit_price = df['Close'].iloc[i]
            exit_date = df.index[i]
            profit = (exit_price - entry_price) / entry_price * 100
            trades.append({
                "Entry Date": entry_date,
                "Exit Date": exit_date,
                "Entry Price": entry_price,
                "Exit Price": exit_price,
                "Profit (%)": round(profit, 2)
            })
            position = None

# Convert to DataFrame
bt_df = pd.DataFrame(trades)

if not bt_df.empty:
    total_trades = len(bt_df)
    winning_trades = bt_df[bt_df['Profit (%)'] > 0]
    win_rate = (len(winning_trades) / total_trades) * 100
    total_profit = bt_df['Profit (%)'].sum()
    avg_profit = bt_df['Profit (%)'].mean()

    # Metrics
    colbt1, colbt2, colbt3, colbt4 = st.columns(4)
    colbt1.metric("Total Trades", total_trades)
    colbt2.metric("Win Rate", f"{win_rate:.2f}%")
    colbt3.metric("Total Return", f"{total_profit:.2f}%")
    colbt4.metric("Avg Profit/Trade", f"{avg_profit:.2f}%")

    # Equity Curve (Cumulative Return)
    bt_df['Cumulative Return'] = bt_df['Profit (%)'].cumsum()
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=bt_df['Exit Date'], y=bt_df['Cumulative Return'],
                              mode='lines+markers', name='Cumulative Return', line=dict(color='green')))
    fig2.update_layout(title="📈 Cumulative Return Curve", xaxis_title="Date", yaxis_title="Cumulative Profit (%)")
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("🔍 Show Trade Log"):
        st.dataframe(bt_df)

else:
    st.warning("⚠️ Not enough crossover signals for backtest during selected date range.")

