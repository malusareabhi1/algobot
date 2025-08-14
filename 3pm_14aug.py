import streamlit as st
import pandas as pd
import yfinance as yf
import datetime as dt
import pytz
import plotly.graph_objects as go

st.title("📈 Nifty 50 Live Candle Chart with 3PM Lines (IST)")

# ------------------- FETCH LIVE NIFTY DATA -------------------
def get_live_nifty_data(interval="1m"):
    """
    Fetch recent Nifty 50 data from Yahoo Finance.
    Converts Datetime to IST timezone.
    """
    ticker = "^NSEI"  # Nifty 50
    df = yf.download(tickers=ticker, period="5d", interval=interval)
    df = df.reset_index()
    df.rename(columns={"Datetime":"Datetime","Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"}, inplace=True)
    
    # Convert to IST
    df['Datetime'] = df['Datetime'].dt.tz_localize('UTC').dt.tz_convert('Asia/Kolkata')
    return df

# ------------------- GET PREVIOUS DAY 3PM CANDLE -------------------
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

# ------------------- PLOT CANDLE CHART -------------------
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

    if high_line and low_line:
        fig.add_hline(y=high_line, line_dash="dash", line_color="green", annotation_text="Prev 3PM High")
        fig.add_hline(y=low_line, line_dash="dash", line_color="red", annotation_text="Prev 3PM Low")

    fig.update_layout(
        title="Nifty 50 Candle Chart (Market Hours Only)",
        xaxis_title="Time (IST)",
        yaxis_title="Price",
        xaxis_rangeslider_visible=False
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------- MAIN -------------------
df = get_live_nifty_data()
prev_3pm = get_prev_3pm_candle(df)
if prev_3pm:
    high_line, low_line = prev_3pm
    st.write(f"Previous day 3PM → High: {high_line:.2f}, Low: {low_line:.2f}")
    plot_candle_chart(df, high_line, low_line)
