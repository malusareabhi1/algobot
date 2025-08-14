import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import time
import plotly.graph_objects as go

st.title("📈 Nifty 50 3PM Candle Strategy Simulator")

# ------------------- SIMULATED DATA -------------------
@st.cache_data
def load_sample_data():
    """
    Simulate Nifty minute data for 2 days
    Columns: Datetime, Open, High, Low, Close
    """
    start_dt = dt.datetime.combine(dt.date.today() - dt.timedelta(days=2), dt.time(9, 15))
    minutes = pd.date_range(start=start_dt, periods=2*390, freq='1min')  # 2 days, 6.5 hours each
    prices = np.cumsum(np.random.randn(len(minutes))) + 18000  # Simulated Nifty around 18000
    df = pd.DataFrame({
        "Datetime": minutes,
        "open": prices + np.random.randn(len(minutes)),
        "high": prices + np.random.rand(len(minutes))*5,
        "low": prices - np.random.rand(len(minutes))*5,
        "close": prices + np.random.randn(len(minutes)),
        "volume": np.random.randint(100, 1000, size=len(minutes))
    })
    return df

df = load_sample_data()

# ------------------- STRATEGY FUNCTION -------------------
def strategy(df):
    df = df.copy()
    df.sort_values("Datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)

    # Previous day 3PM 15-min candle
    prev_day = df['Datetime'].dt.date.max() - dt.timedelta(days=1)
    prev_3pm_candle = df[(df['Datetime'].dt.date == prev_day) &
                          (df['Datetime'].dt.hour == 15) &
                          (df['Datetime'].dt.minute < 15)]
    if prev_3pm_candle.empty:
        st.warning("No 3PM candle data found for previous day!")
        return

    open_3pm = prev_3pm_candle['open'].values[0]
    close_3pm = prev_3pm_candle['close'].values[0]
    high_line = max(open_3pm, close_3pm)
    low_line = min(open_3pm, close_3pm)

    st.write(f"Previous day 3PM candle → Open: {open_3pm:.2f}, Close: {close_3pm:.2f}, High: {high_line:.2f}, Low: {low_line:.2f}")

    # First 15-min candle today (simulate 9:15-9:30)
    today = dt.date.today()
    first_candle = df[(df['Datetime'].dt.date == today) &
                      (df['Datetime'].dt.hour == 9) &
                      (df['Datetime'].dt.minute < 30)]
    if first_candle.empty:
        st.warning("First 15-min candle not found yet.")
        return

    ref_open = first_candle['open'].values[0]
    ref_close = first_candle['close'].values[0]
    ref_high = first_candle['high'].values[0]
    ref_low = first_candle['low'].values[0]

    # Plot candles and lines
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['close'], mode='lines', name='Close'))
    fig.add_hline(y=high_line, line_dash="dash", line_color="green", annotation_text="Prev 3PM High")
    fig.add_hline(y=low_line, line_dash="dash", line_color="red", annotation_text="Prev 3PM Low")
    st.plotly_chart(fig, use_container_width=True)

    # Check trade condition
    trade_signal = None
    if ref_close > high_line and ref_close > low_line:
        trade_signal = "Buy Call"
    elif ref_close < high_line and ref_close < low_line:
        trade_signal = "Buy Put"

    if trade_signal:
        st.success(f"Trade Signal: {trade_signal} at {ref_close:.2f} (Simulated {TRADE_QTY if 'TRADE_QTY' in globals() else 'Qty'} shares)")

strategy(df)
