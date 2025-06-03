import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime

# --- SETTINGS ---
st.set_page_config(page_title="Intraday Volume Breakout", layout="wide")
st.title("📈 Intraday Volume Breakout Strategy (NIFTY 200)")

# --- SIDEBAR ---
st.sidebar.header("Strategy Settings")
try:
    nifty200_tickers = pd.read_csv("ind_nifty200list.csv")
except FileNotFoundError:
    nifty200_tickers = pd.DataFrame({'Symbol': [
        'RELIANCE', 'ICICIBANK', 'INFY', 'TCS', 'HDFCBANK',
        'SBIN', 'AXISBANK', 'ITC', 'LT', 'KOTAKBANK'
    ]})

selected_stocks = st.sidebar.multiselect("Select Stocks", options=nifty200_tickers['Symbol'], default=nifty200_tickers['Symbol'][:5])
from_time = st.sidebar.time_input("From Time", value=datetime.time(9, 30))
to_time = st.sidebar.time_input("To Time", value=datetime.time(15, 15))
volume_multiplier = st.sidebar.slider("Volume Spike Threshold (X times)", 1.0, 5.0, 2.0, 0.1)

# --- STRATEGY FUNCTION ---
def fetch_data(symbol):
    data = yf.download(symbol + ".NS", period="1d", interval="5m", progress=False)
    if data.empty:
        raise ValueError("No intraday data returned.")
    data.dropna(inplace=True)
    return data

def apply_strategy(df, volume_multiplier):
    df = df.copy()
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    df['VolumeAvg'] = df['Volume'].rolling(window=10).mean()

    # Drop rows with NaNs in required columns
    df.dropna(subset=['Close', 'EMA20', 'VWAP', 'VolumeAvg', 'High', 'Volume'], inplace=True)

    # Strategy conditions
    conditions = (
        (df['Close'] > df['EMA20']) &
        (df['Close'] > df['VWAP']) &
        (df['Volume'] > volume_multiplier * df['VolumeAvg']) &
        (df['Close'] > df['High'].shift(1))
    )

    df['Signal'] = np.where(conditions, 'BUY', '')
    return df

# --- MAIN LOGIC ---
stocks_with_signals = []
for stock in selected_stocks:
    try:
        df = fetch_data(stock)
        df.index = pd.to_datetime(df.index)

        # Time-based filtering
        df = df[(df.index.time >= from_time) & (df.index.time <= to_time)]
        if df.empty:
            st.warning(f"No data available for {stock} in the selected time window.")
            continue

        df = apply_strategy(df, volume_multiplier)
        signals = df[df['Signal'] == 'BUY']

        if not signals.empty:
            stocks_with_signals.append((stock, signals.iloc[-1]))
            st.subheader(f"📌 {stock} Signal")
            st.write(signals.tail())
            st.line_chart(df[['Close', 'EMA20', 'VWAP']])
    except Exception as e:
        st.warning(f"⚠️ Failed to process {stock}: {e}")

if not stocks_with_signals:
    st.info("✅ No breakout signals detected in the selected time window.")
