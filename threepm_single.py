import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta
import yfinance as yf

st.set_page_config(page_title="Base Zone Swing Strategy", layout="wide")

st.title("📈 Base Zone Swing Strategy – NIFTY (15 Min)")

# --------------------------------------------------
# DATA
# --------------------------------------------------
@st.cache_data
def load_data(symbol, days=15):
    df = yf.download(
        symbol,
        interval="15m",
        period=f"{days}d",
        progress=False
    )
    df.reset_index(inplace=True)
    df.rename(columns={
        "Datetime": "Datetime",
        "Open": "Open_^NSEI",
        "High": "High_^NSEI",
        "Low": "Low_^NSEI",
        "Close": "Close_^NSEI"
    }, inplace=True)
    return df.dropna()

df = load_data("^NSEI")
st.write(df)
# --------------------------------------------------
# SIGNAL DETECTOR (ONE CANDLE ONLY)
# --------------------------------------------------
def detect_signal_at_candle(df, qty):
    latest = df.tail(1)   # keep as DataFrame

    # ✅ Extract SCALAR datetime
    dt = latest['Datetime'].iloc[0]
    spot = latest['Close_^NSEI'].iloc[0]

    prev_day = (dt - pd.Timedelta(days=1)).date()

    candle_3pm = df[
        (df['Datetime'].dt.date == prev_day) &
        (df['Datetime'].dt.hour == 15) &
        (df['Datetime'].dt.minute == 0)
    ]

    if candle_3pm.empty:
        return None

    base_open = candle_3pm.iloc[0]['Open_^NSEI']
    base_close = candle_3pm.iloc[0]['Close_^NSEI']
    base_low = min(base_open, base_close)
    base_high = max(base_open, base_close)

    H = latest['High_^NSEI'].iloc[0]
    L = latest['Low_^NSEI'].iloc[0]
    C = latest['Close_^NSEI'].iloc[0]

    swing_low = df.tail(10)['Low_^NSEI'].min()
    swing_high = df.tail(10)['High_^NSEI'].max()

    # CONDITION 1 – CALL
    if (L < base_high and H > base_low) and C > base_high:
        return {
            "Time": dt,
            "Signal": "CALL",
            "Entry": H,
            "StopLoss": swing_low,
            "Qty": qty,
            "Spot": spot
        }

    # CONDITION 4 – PUT
    if (L < base_high and H > base_low) and C < base_low:
        return {
            "Time": dt,
            "Signal": "PUT",
            "Entry": L,
            "StopLoss": swing_high,
            "Qty": qty,
            "Spot": spot
        }

    return None

# --------------------------------------------------
# TRADE MONITOR
# --------------------------------------------------
def monitor_trade(trade, candle):
    if trade["Type"] == "CALL":
        if candle['Low_^NSEI'] <= trade['StopLoss']:
            trade["ExitTime"] = candle['Datetime']
            trade["Exit"] = trade['StopLoss']
            trade["Status"] = "Exited SL"

    if trade["Type"] == "PUT":
        if candle['High_^NSEI'] >= trade['StopLoss']:
            trade["ExitTime"] = candle['Datetime']
            trade["Exit"] = trade['StopLoss']
            trade["Status"] = "Exited SL"

    # Time Exit – 16 minutes
    if candle['Datetime'] >= trade['EntryTime'] + timedelta(minutes=16):
        trade["ExitTime"] = candle['Datetime']
        trade["Exit"] = candle['Close_^NSEI']
        trade["Status"] = "Exited Time"

    return trade

# --------------------------------------------------
# ENGINE – LOOP ALL CANDLES
# --------------------------------------------------
def generate_all_signals(df, qty):
    results = []
    active_trade = None

    for i in range(20, len(df)):
        slice_df = df.iloc[:i+1]
        candle = slice_df.iloc[-1]

        if active_trade:
            active_trade = monitor_trade(active_trade, candle)
            if active_trade["Status"] != "Active":
                active_trade["PnL"] = (
                    active_trade["Exit"] - active_trade["Entry"]
                    if active_trade["Type"] == "CALL"
                    else active_trade["Entry"] - active_trade["Exit"]
                )
                results.append(active_trade)
                active_trade = None
            continue

        signal = detect_signal_at_candle(slice_df, qty)
        if signal:
            active_trade = signal

    return pd.DataFrame(results)

# --------------------------------------------------
# USER INPUTS
# --------------------------------------------------
qty = st.number_input("Quantity", value=750, step=75)

if st.button("🚀 Run Strategy"):
    with st.spinner("Scanning candles..."):
        result_df = generate_all_signals(df, qty)

    if result_df.empty:
        st.warning("No signals found")
    else:
        st.success(f"Total Trades: {len(result_df)}")

        st.dataframe(
            result_df.style
            .format({
                "Entry": "₹{:.2f}",
                "Exit": "₹{:.2f}",
                "PnL": "₹{:.2f}"
            })
        )

        st.metric("Total PnL", f"₹{result_df['PnL'].sum():.2f}")
