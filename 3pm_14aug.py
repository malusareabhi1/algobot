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
    Simulate Nifty minute data for 2 days (9:15 AM to 3:30 PM)
    """
    minutes_list = []
    prices_list = []

    for d in range(2):  # 2 days
        date = dt.date.today() - dt.timedelta(days=2 - d)
        # Trading from 9:15 to 15:30 → 6h 15min = 375 minutes
        minutes = pd.date_range(start=dt.datetime.combine(date, dt.time(9,15)), periods=375, freq='1min')
        prices = np.cumsum(np.random.randn(len(minutes))) + 18000  # simulated around 18000
        minutes_list.append(minutes)
        prices_list.append(prices)

    all_minutes = pd.concat([pd.Series(m) for m in minutes_list])
    all_prices = np.concatenate(prices_list)

    df = pd.DataFrame({
        "Datetime": all_minutes,
        "open": all_prices + np.random.randn(len(all_minutes)),
        "high": all_prices + np.random.rand(len(all_minutes))*5,
        "low": all_prices - np.random.rand(len(all_minutes))*5,
        "close": all_prices + np.random.randn(len(all_minutes)),
        "volume": np.random.randint(100,1000,len(all_minutes))
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

# ------------------- STRATEGY LOGIC -------------------
# ------------------- FUNCTION TO GET PREVIOUS 3PM CANDLE -------------------
def get_prev_3pm_candle(df):
    prev_day = df['Datetime'].dt.date.max() - dt.timedelta(days=1)
    prev_3pm_candle = df[(df['Datetime'].dt.date == prev_day) &
                          (df['Datetime'].dt.hour == 15) &
                          (df['Datetime'].dt.minute == 0)]
    if prev_3pm_candle.empty:
        st.warning("No 3PM candle found for previous day!")
        return None
    open_3pm = prev_3pm_candle['open'].values[0]
    close_3pm = prev_3pm_candle['close'].values[0]
    high_line = max(open_3pm, close_3pm)
    low_line = min(open_3pm, close_3pm)
    return high_line, low_line
# ------------------- FUNCTION TO PLOT CANDLE CHART -------------------
def plot_candle_chart(df, high_line=None, low_line=None):
    # Filter only market hours
    df = df[(df['Datetime'].dt.time >= dt.time(9, 15)) & (df['Datetime'].dt.time <= dt.time(15, 30))]

    fig = go.Figure(data=[go.Candlestick(
        x=df['Datetime'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Nifty 50'
    )])

    # Add previous 3PM candle lines
    if high_line and low_line:
        fig.add_hline(y=high_line, line_dash="dash", line_color="green", annotation_text="Prev 3PM High")
        fig.add_hline(y=low_line, line_dash="dash", line_color="red", annotation_text="Prev 3PM Low")

    fig.update_layout(
        title="Nifty 50 Candle Chart (Market Hours Only)",
        xaxis_title="Time",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------- EXECUTION -------------------
prev_3pm = get_prev_3pm_candle(df)
if prev_3pm:
    high_line, low_line = prev_3pm
    st.write(f"Previous day 3PM → High: {high_line:.2f}, Low: {low_line:.2f}")
    plot_candle_chart(df, high_line, low_line)
# ------------------- EXECUTION -------------------
prev_3pm = get_prev_3pm_candle(df)
if prev_3pm:
    open_3pm, close_3pm, high_line, low_line = prev_3pm
    st.write(f"Previous day 3PM candle → Open: {open_3pm:.2f}, Close: {close_3pm:.2f}, High: {high_line:.2f}, Low: {low_line:.2f}")

    # Take first 15-min candle today as reference
    today = dt.date.today()
    first_candle = df[(df['Datetime'].dt.date == today) & (df['Datetime'].dt.hour == 9) & (df['Datetime'].dt.minute < 30)]
    if not first_candle.empty:
        ref_candle = {
            "high": first_candle['high'].values[0],
            "low": first_candle['low'].values[0]
        }
        st.write(f"Reference Candle → High: {ref_candle['high']:.2f}, Low: {ref_candle['low']:.2f}")
    else:
        ref_candle = None

    # Plot chart
    plot_nifty_chart(df, high_line=high_line, low_line=low_line, ref_candle=ref_candle)
