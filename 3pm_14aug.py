import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import datetime
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
    Plots 15-min Nifty candles for last 2 trading days with previous day's 3PM candle highlighted.
    Only the 3PM candle lines get annotations.
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
        high_3pm = max(open_3pm, close_3pm)
        low_3pm = min(open_3pm, close_3pm)
        candle_time = candle_3pm.iloc[0]['Datetime']
    else:
        open_3pm = close_3pm = high_3pm = low_3pm = candle_time = None
        st.warning("No 3:00 PM candle found for last trading day.")

    # Plot candlestick chart
    fig = go.Figure(data=[go.Candlestick(
        x=df_plot['Datetime'],
        open=df_plot['Open_^NSEI'],
        high=df_plot['High_^NSEI'],
        low=df_plot['Low_^NSEI'],
        close=df_plot['Close_^NSEI']
    )])

    # Highlight 3PM candle with a shaded rectangle
    if candle_time:
        fig.add_shape(
            type="rect",
            x0=candle_time,
            x1=candle_time + pd.Timedelta(minutes=15),
            y0=low_3pm,
            y1=high_3pm,
            fillcolor="LightSkyBlue",
            opacity=0.3,
            line_width=0,
            layer="below"
        )

    # Only 3PM candle lines get annotations
    if open_3pm:
        fig.add_hline(y=open_3pm, line_dash="dot", line_color="blue",
                      annotation_text="3PM Open", annotation_position="top left")
    if close_3pm:
        fig.add_hline(y=close_3pm, line_dash="dot", line_color="red",
                      annotation_text="3PM Close", annotation_position="top left")

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
# ----------------------------------------------------------------

LOT_SIZE = 75
TRADE_QTY = 10 * LOT_SIZE
PROFIT_PERCENT = 0.10  # 10% gain
TIME_EXIT_MIN = 16  # minutes

def get_prev_3pm_candle(df):
    """Get previous day's 3PM 15-min candle."""
    df = df.sort_values("Datetime")
    prev_day = df['Datetime'].dt.date.max() - dt.timedelta(days=1)
    candle_3pm = df[(df['Datetime'].dt.date == prev_day) &
                     (df['Datetime'].dt.hour == 15) &
                     (df['Datetime'].dt.minute == 0)]
    if candle_3pm.empty:
        return None
    open_3pm = candle_3pm.iloc[0]['Open_^NSEI']
    close_3pm = candle_3pm.iloc[0]['Close_^NSEI']
    high_3pm = max(open_3pm, close_3pm)
    low_3pm = min(open_3pm, close_3pm)
    return {"open": open_3pm, "close": close_3pm, "high": high_3pm, "low": low_3pm}

def check_trade_condition(df, prev_3pm):
    """
    df: Nifty 15-min candles for current day
    prev_3pm: dict containing open, close, high, low of previous day's 3PM candle
    Returns: dict with trade_signal, trade_type, entry_price, stoploss, target, exit_time
    """
    today = df['Datetime'].dt.date.max()
    first_candle = df[(df['Datetime'].dt.date == today) &
                      (df['Datetime'].dt.hour == 9) &
                      (df['Datetime'].dt.minute < 30)]
    if first_candle.empty:
        return None  # first candle not yet formed

    ref_open = first_candle['open'].values[0]
    ref_close = first_candle['close'].values[0]
    ref_high = first_candle['high'].values[0]
    ref_low = first_candle['low'].values[0]

    trade = None
    entry_price = None
    trade_type = None

    # ----------------- Condition 1 -----------------
    if ref_close > prev_3pm['high'] and ref_close > prev_3pm['low']:
        trade = "Buy Call"
        trade_type = "CE"
        entry_price = ref_close

    # ----------------- Condition 2 -----------------
    elif ref_close < prev_3pm['low']:  # major gap down
        # Reference candle 2
        ref2_high = ref_high
        ref2_low = ref_low
        trade = "Buy Put"
        trade_type = "PE"
        entry_price = ref2_low  # trade triggered when next candle crosses this

    # ----------------- Condition 3 -----------------
    elif ref_close > prev_3pm['high']:  # major gap up
        ref2_high = ref_high
        ref2_low = ref_low
        trade = "Buy Call"
        trade_type = "CE"
        entry_price = ref2_high

    # ----------------- Condition 4 -----------------
    elif ref_close < prev_3pm['low']:
        trade = "Buy Put"
        trade_type = "PE"
        entry_price = ref_close

    if trade:
        stoploss = entry_price * 0.90  # 10% trailing SL
        target = entry_price * 1.10  # 10% profit for 50% position
        exit_time = first_candle['Datetime'].values[0] + pd.Timedelta(minutes=TIME_EXIT_MIN)
        return {
            "trade_signal": trade,
            "trade_type": trade_type,
            "entry_price": entry_price,
            "stoploss": stoploss,
            "target": target,
            "qty": TRADE_QTY,
            "expiry": "nearest_weekly",
            "exit_time": exit_time
        }
    return None
# ------------------- STREAMLIT INTERFACE -------------------
st.title("📈 Nifty 15-min Live Candles with 3PM Lines")



# Placeholder for chart
chart_placeholder = st.empty()
trade_placeholder = st.empty()

# Infinite loop for live updates
while True:
    # Load Nifty 15-min data (replace with your function)
    df = load_nifty_data()  

    if df.empty:
        st.warning("No data loaded.")
        time.sleep(60)
        continue

    # 1️⃣ Get previous day's 3PM candle
    prev_3pm = get_prev_3pm_candle(df)

    if prev_3pm is None:
        st.warning("No 3PM candle found for previous day.")
        time.sleep(60)
        continue

    # 2️⃣ Check trade conditions
    trade_info = check_trade_condition(df, prev_3pm)

    # 3️⃣ Plot chart with 3PM horizontal lines
    with chart_placeholder:
        plot_nifty_candles(df, prev_3pm)  # Pass prev_3pm to mark lines

    # 4️⃣ Display trade signal if any
    with trade_placeholder:
        if trade_info:
            st.success(f"Trade Signal: {trade_info['trade_signal']}\n"
                       f"Type: {trade_info['trade_type']}\n"
                       f"Entry: {trade_info['entry_price']:.2f}\n"
                       f"Stoploss: {trade_info['stoploss']:.2f}\n"
                       f"Target: {trade_info['target']:.2f}\n"
                       f"Qty: {trade_info['qty']}\n"
                       f"Expiry: {trade_info['expiry']}\n"
                       f"Time Exit: {trade_info['exit_time']}")
        else:
            st.info("No trade signal currently.")

    # 5️⃣ Wait before refreshing
    time.sleep(60)
