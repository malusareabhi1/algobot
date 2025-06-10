import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="200MA + 44MA Strategy", layout="wide")
st.title("📈 200 MA + 44 MA Crossover Strategy Dashboard")

# Sidebar input
symbol = st.sidebar.text_input("Enter NSE Symbol (e.g. RELIANCE.NS)", "RELIANCE.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))

# Fetch data
@st.cache_data
def fetch_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    df.dropna(inplace=True)
    return df

df = fetch_data(symbol, start_date, end_date)

# Ensure sufficient data
if len(df) < 200:
    st.warning("Not enough data to calculate 200 MA.")
    st.stop()

# Calculate Moving Averages
df['MA44'] = df['Close'].rolling(window=44).mean()
df['MA200'] = df['Close'].rolling(window=200).mean()

# Generate signals
df['Signal'] = 0
df['Signal'] = np.where(df['MA44'] > df['MA200'], 1, 0)
df['Crossover'] = df['Signal'].diff()

# Get latest signal
last_signal = df['Signal'].iloc[-1]
signal_text = "✅ BUY" if last_signal == 1 else "🔻 SELL"
trend = "Bullish (MA44 > MA200)" if last_signal == 1 else "Bearish (MA44 < MA200)"

# Plot
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'],
    high=df['High'],
    low=df['Low'],
    close=df['Close'],
    name="Candles"
))
fig.add_trace(go.Scatter(
    x=df.index, y=df['MA44'],
    line=dict(color='blue', width=1),
    name="44 MA"
))
fig.add_trace(go.Scatter(
    x=df.index, y=df['MA200'],
    line=dict(color='orange', width=1),
    name="200 MA"
))
fig.update_layout(title=f"{symbol} - 44MA vs 200MA", xaxis_rangeslider_visible=False, height=600)

# Show output
st.plotly_chart(fig, use_container_width=True)

col1, col2, col3 = st.columns(3)
col1.metric("Last Close", f"₹{df['Close'].iloc[-1]:.2f}")
col2.metric("Trend", trend)
col3.metric("Signal", signal_text)

# Show crossover signals table
show_table = st.sidebar.checkbox("Show Crossover Signal Dates")

if show_table:
    signal_dates = df[df['Crossover'].abs() == 1][['Close', 'MA44', 'MA200']]
    signal_dates['Action'] = np.where(df['Crossover'] == 1, 'BUY', 'SELL')
    st.subheader("📅 Crossover Signal History")
    st.dataframe(signal_dates.tail(10))
