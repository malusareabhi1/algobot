import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go


st.set_page_config("🪤 TRAP Strategy Dashboard", layout="wide")
st.title("🪤 TRAP Strategy (False Breakout Reversal Detector)")

# Sidebar Inputs
symbol = st.sidebar.text_input("Enter NSE Symbol (e.g. RELIANCE.NS)", value="RELIANCE.NS")
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2025-06-10"))

# Fetch Data
@st.cache_data
def load_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    df.dropna(inplace=True)
    return df

df = load_data(symbol, start_date, end_date)

# Compute Rolling Support/Resistance
df['20High'] = df['High'].rolling(window=20).max()
df['20Low'] = df['Low'].rolling(window=20).min()

# Detect TRAPs
signals = []

for i in range(21, len(df) - 1):
    try:
        today_high = float(df['High'].iloc[i])
        today_low = float(df['Low'].iloc[i])
        today_close = float(df['Close'].iloc[i])
        prior_20high = float(df['20High'].iloc[i - 1])
        prior_20low = float(df['20Low'].iloc[i - 1])
        next_close = float(df['Close'].iloc[i + 1])
        next_date = df.index[i + 1]

        # False Breakout Above (SELL TRAP)
        if today_high > prior_20high and next_close < today_close:
            signals.append((next_date, next_close, 'SELL TRAP'))

        # False Breakdown Below (BUY TRAP)
        elif today_low < prior_20low and next_close > today_close:
            signals.append((next_date, next_close, 'BUY TRAP'))
    except:
        continue


# Create Signal DataFrame
signal_df = pd.DataFrame(signals, columns=['Date', 'Price', 'Signal']).set_index('Date')

# Plot Chart
fig = go.Figure()

# Candlestick
fig.add_trace(go.Candlestick(
    x=df.index,
    open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
    name="Price"
))

# TRAP signals
buy_signals = signal_df[signal_df['Signal'] == 'BUY TRAP']
sell_signals = signal_df[signal_df['Signal'] == 'SELL TRAP']

fig.add_trace(go.Scatter(
    x=buy_signals.index, y=buy_signals['Price'],
    mode='markers', name='BUY TRAP',
    marker=dict(color='green', size=10, symbol='triangle-up')
))

fig.add_trace(go.Scatter(
    x=sell_signals.index, y=sell_signals['Price'],
    mode='markers', name='SELL TRAP',
    marker=dict(color='red', size=10, symbol='triangle-down')
))

fig.update_layout(
    title=f"{symbol} - TRAP Strategy Signals",
    xaxis_title="Date", yaxis_title="Price",
    xaxis_rangeslider_visible=False,
    height=600
)

st.plotly_chart(fig, use_container_width=True)

# Show table
st.subheader("📋 Signal Log")
if not signal_df.empty:
    st.dataframe(signal_df)
else:
    st.info("No TRAP signals detected in the selected period.")
