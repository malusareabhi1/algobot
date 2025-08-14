import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# ------------------- FUNCTION 1: LOAD DATA -------------------
def load_nifty_data():
    """
    Load Nifty 15-min data from Yahoo Finance for last 7 days + today.
    Converts datetime to Asia/Kolkata timezone.
    Returns: DataFrame with Datetime column
    """
    today = datetime.today().date()
    start_date = today - timedelta(days=7)
    end_date = today + timedelta(days=1)

    df = yf.download("^NSEI", start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"), interval="15m")
    if df.empty:
        return pd.DataFrame()

    df.reset_index(inplace=True)

    # Flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ['_'.join(col).strip() if isinstance(col, tuple) else col for col in df.columns]

    # Rename datetime column
    if 'Datetime_' in df.columns:
        df.rename(columns={'Datetime_': 'Datetime'}, inplace=True)
    elif 'Date' in df.columns:
        df.rename(columns={'Date': 'Datetime'}, inplace=True)

    # Convert to datetime & timezone aware
    if df['Datetime'].dt.tz is None:
        df['Datetime'] = df['Datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    else:
        df['Datetime'] = df['Datetime'].dt.tz_convert('Asia/Kolkata')

    return df

# ------------------- FUNCTION 2: PLOT CHART -------------------
def plot_nifty_candles(df):
    """
    Plots 15-min Nifty candles for last 2 trading days with previous day's 3PM candle lines.
    """
    if df.empty:
        st.warning("No data available.")
        return

    unique_days = df['Datetime'].dt.date.unique()
    if len(unique_days) < 2:
        st.warning("Not enough data for two trading days")
        return

    last_day = unique_days[-2]
    today = unique_days[-1]
    df_plot = df[df['Datetime'].dt.date.isin([last_day, today])]

    # Previous day 3PM candle
    candle_3pm = df_plot[(df_plot['Datetime'].dt.date == last_day) &
                         (df_plot['Datetime'].dt.hour == 15) &
                         (df_plot['Datetime'].dt.minute == 0)]
    if not candle_3pm.empty:
        open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
        close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
    else:
        open_3pm = close_3pm = None
        st.warning("No 3:00 PM candle found for last trading day.")

    # Plot candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=df_plot['Datetime'],
        open=df_plot['Open_^NSEI'],
        high=df_plot['High_^NSEI'],
        low=df_plot['Low_^NSEI'],
        close=df_plot['Close_^NSEI']
    )])

    # Add 3PM candle lines
    if open_3pm and close_3pm:
        fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue", annotation_text="3PM Open")
        fig.add_hline(y=close_3pm, line_dash="dot", line_color="red", annotation_text="3PM Close")

    # Hide weekends and hours outside trading
    fig.update_layout(title="Nifty 15-min candles - Last Day & Today", xaxis_rangeslider_visible=False)
    fig.update_layout(
        xaxis=dict(
            rangebreaks=[
                dict(bounds=["sat", "mon"]),       # hide weekends
                dict(bounds=[15.5, 9.25], pattern="hour")  # hide off-market hours
            ]
        )
    )

    st.plotly_chart(fig, use_container_width=True)

# ------------------- STREAMLIT INTERFACE -------------------
st.title("📈 Nifty 15-min Live Candles with 3PM Lines")

# Create a placeholder container for dynamic updates
chart_placeholder = st.empty()

# Infinite loop for live updates
while True:
    df = load_nifty_data()
    with chart_placeholder:
        plot_nifty_candles(df)
    time.sleep(60)  # Refresh every minute
