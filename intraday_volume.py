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
#nifty200_tickers = pd.read_csv("https://archives.nseindia.com/content/indices/ind_nifty200list.csv")
nifty200_tickers = pd.read_csv("ind_nifty200list.csv")
selected_stocks = st.sidebar.multiselect("Select Stocks", options=nifty200_tickers['Symbol'], default=nifty200_tickers['Symbol'][:5])
from_time = st.sidebar.time_input("From Time", value=datetime.time(9, 30))
to_time = st.sidebar.time_input("To Time", value=datetime.time(15, 15))
volume_multiplier = st.sidebar.slider("Volume Spike Threshold (X times)", 1.0, 5.0, 2.0, 0.1)

# --- STRATEGY FUNCTION ---
def fetch_data(symbol):
    data = yf.download(symbol + ".NS", period="1d", interval="5m")
    data.dropna(inplace=True)
    return data

def apply_strategy(df, volume_multiplier):
    df['EMA20'] = df['Close'].ewm(span=20).mean()
    df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    df['VolumeAvg'] = df['Volume'].rolling(window=10).mean()

    conditions = (
        (df['Close'] > df['EMA20']) &
        (df['Close'] > df['VWAP']) &
        (df['Volume'] > volume_multiplier * df['VolumeAvg']) &
        (df['Close'] > df['High'].shift(1))
    )
    df['Signal'] = np.where(conditions, 'BUY', '')
    return df

# --- MAIN LOOP ---
stocks_with_signals = []
for stock in selected_stocks:
    try:
        df = fetch_data(stock)
        df = df.between_time(str(from_time), str(to_time))
        df = apply_strategy(df, volume_multiplier)
        signals = df[df['Signal'] == 'BUY']
        if not signals.empty:
            stocks_with_signals.append((stock, signals.iloc[-1]))
            st.subheader(f"📌 {stock} Signal")
            st.write(signals.tail())
            st.line_chart(df[['Close', 'EMA20', 'VWAP']])
    except Exception as e:
        st.warning(f"Failed to fetch {stock}: {e}")

if not stocks_with_signals:
    st.info("No breakout signals detected in the selected time window.")
