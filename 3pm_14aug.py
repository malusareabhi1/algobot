import streamlit as st
import pandas as pd
import numpy as np
import datetime as dt
import time
from kiteconnect import KiteConnect  # Zerodha API
import plotly.graph_objects as go
from dotenv import load_dotenv
import os
# ------------------- USER SETTINGS -------------------
#KITE_API_KEY = "YOUR_API_KEY"
#KITE_ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
# Get API key and access token from environment
KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN")
NIFTY_TOKEN = 256265  # Nifty 50 spot
LOT_SIZE = 75
TRADE_QTY = 10 * LOT_SIZE  # 10 lots
PROFIT_PERCENT = 0.10  # 10% premium gain
TIME_EXIT_MIN = 16  # minutes after trade execution

# Initialize Kite
kite = KiteConnect(api_key=KITE_API_KEY)
kite.set_access_token(KITE_ACCESS_TOKEN)

st.title("📈 Nifty 50 Live 3PM Candle Strategy + ITM Option Trading")

# ------------------- FUNCTION TO GET LIVE DATA -------------------
def get_live_nifty_minute_data(token, interval="minute"):
    """
    Fetch live Nifty minute data from Zerodha.
    Returns: DataFrame with Datetime, Open, High, Low, Close
    """
    # You can use kite.historical_data to get last 2 days for previous 3PM candle
    today = dt.date.today()
    from_date = today - dt.timedelta(days=2)
    to_date = today
    df = pd.DataFrame(kite.historical_data(NIFTY_TOKEN , from_date, to_date, interval))
    df['Datetime'] = pd.to_datetime(df['date'])
    df = df[['Datetime', 'open', 'high', 'low', 'close', 'volume']]
    return df

# ------------------- STRATEGY LOGIC -------------------
def strategy(df):
    """
    df: Nifty minute data including previous day
    """
    df = df.copy()
    df.sort_values("Datetime", inplace=True)
    df.reset_index(drop=True, inplace=True)
    
    # ----- Step 1: Previous day 3 PM 15-min candle -----
    prev_day = df['Datetime'].dt.date.max() - dt.timedelta(days=1)
    prev_3pm_candle = df[(df['Datetime'].dt.date == prev_day) &
                          (df['Datetime'].dt.hour == 15) &
                          (df['Datetime'].dt.minute >= 0) &
                          (df['Datetime'].dt.minute < 15)]
    if prev_3pm_candle.empty:
        st.warning("No 3PM candle data found for previous day!")
        return
    open_3pm = prev_3pm_candle['open'].values[0]
    close_3pm = prev_3pm_candle['close'].values[0]
    high_line = max(open_3pm, close_3pm)
    low_line = min(open_3pm, close_3pm)

    st.write(f"Previous day 3PM candle → Open: {open_3pm}, Close: {close_3pm}, High: {high_line}, Low: {low_line}")

    # ----- Step 2: First 15-min candle today (9:15-9:30 AM) -----
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

    # Plot previous 3PM lines
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Datetime'], y=df['close'], mode='lines', name='Close'))
    fig.add_hline(y=high_line, line_dash="dash", line_color="green", annotation_text="Prev 3PM High")
    fig.add_hline(y=low_line, line_dash="dash", line_color="red", annotation_text="Prev 3PM Low")
    st.plotly_chart(fig, use_container_width=True)

    # ----- Step 3: Determine trade conditions -----
    trade_signal = None
    trade_price = None
    trade_type = None  # Call or Put

    # Scenario 1: First candle crosses previous 3PM lines from below → Buy Call
    if ref_close > high_line and ref_close > low_line:
        trade_signal = "Buy Call"
        trade_price = ref_close
        trade_type = "CE"
    # Scenario 2: Gap down first candle closes below previous 3PM → Reference candle 2
    elif ref_close < high_line and ref_close < low_line:
        trade_signal = "Buy Put"
        trade_price = ref_close
        trade_type = "PE"
    # Scenario 3: Gap up first candle closes above previous 3PM → Reference candle 2
    elif ref_close > high_line and ref_close > low_line:
        trade_signal = "Buy Call"
        trade_price = ref_close
        trade_type = "CE"
    # Scenario 4: First candle crosses previous 3PM from above → Buy Put
    elif ref_close < high_line and ref_close < low_line:
        trade_signal = "Buy Put"
        trade_price = ref_close
        trade_type = "PE"

    if trade_signal:
        st.success(f"Trade Signal: {trade_signal} at {trade_price} (Qty: {TRADE_QTY})")
        # You can call Kite order here
        # kite.place_order(tradingsymbol="NIFTYxxxx", exchange="NFO", transaction_type="BUY", ...)
    
    st.write("Waiting for next candle to check for reference candle 2 triggers...")

# ------------------- MAIN LOOP -------------------
while True:
    df = get_live_nifty_minute_data(NIFTY_TOKEN)
    strategy(df)
    time.sleep(60)  # Refresh every minute
