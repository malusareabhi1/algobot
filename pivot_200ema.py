import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime as dt

# -------------------
# Indicator Functions
# -------------------

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def supertrend(df, period=10, multiplier=3):
    hl2 = (df['High'] + df['Low']) / 2
    atr = df['High'].rolling(period).max() - df['Low'].rolling(period).min()
    atr = atr.ewm(alpha=1/period, adjust=False).mean()

    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    st_dir = [True] * len(df)  # True = bullish, False = bearish
    st_val = [0] * len(df)

    for i in range(1, len(df)):
        if df['Close'][i] > upperband[i-1]:
            st_dir[i] = True
        elif df['Close'][i] < lowerband[i-1]:
            st_dir[i] = False
        else:
            st_dir[i] = st_dir[i-1]
            if st_dir[i] and lowerband[i] < lowerband[i-1]:
                lowerband[i] = lowerband[i-1]
            if not st_dir[i] and upperband[i] > upperband[i-1]:
                upperband[i] = upperband[i-1]

        st_val[i] = lowerband[i] if st_dir[i] else upperband[i]

    df['Supertrend'] = st_val
    df['ST_Dir'] = st_dir
    return df

def pivot_points(df):
    last = df.iloc[-2]  # Use yesterday's OHLC for today's pivots
    P = (last['High'] + last['Low'] + last['Close']) / 3
    R1 = 2*P - last['Low']
    S1 = 2*P - last['High']
    R2 = P + (last['High'] - last['Low'])
    S2 = P - (last['High'] - last['Low'])
    return P, R1, S1, R2, S2

# -------------------
# Scanner Logic
# -------------------
def check_signal(df):
    if len(df) < 200:
        return None

    df['EMA200'] = ema(df['Close'], 200)
    df = supertrend(df)

    P, R1, S1, R2, S2 = pivot_points(df)
    last = df.iloc[-1]

    if last['Close'] > last['EMA200'] and last['ST_Dir'] and last['Close'] > P:
        return {"Signal": "BUY", "Target": R1, "SL": last['Supertrend']}
    elif last['Close'] < last['EMA200'] and not last['ST_Dir'] and last['Close'] < P:
        return {"Signal": "SELL", "Target": S1, "SL": last['Supertrend']}
    return None

# -------------------
# Streamlit App
# -------------------
st.set_page_config(page_title="Swing Scanner – Supertrend + Pivot + EMA200", layout="wide")
st.title("📊 NSE Swing Trading Scanner – Supertrend + Pivot + EMA200")

nse_symbols = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", 
    "SBIN.NS", "HINDUNILVR.NS", "KOTAKBANK.NS", "ITC.NS", "LT.NS"
]  # You can replace this with NIFTY 100 list

start = dt.date.today() - dt.timedelta(days=300)
end = dt.date.today()

results = []
for symbol in nse_symbols:
    try:
        df = yf.download(symbol, start=start, end=end, interval="1d")
        df.dropna(inplace=True)
        sig = check_signal(df)
        if sig:
            results.append({
                "Stock": symbol.replace(".NS", ""),
                "Signal": sig["Signal"],
                "Close": round(df['Close'].iloc[-1], 2),
                "Target": round(sig["Target"], 2),
                "Stop Loss": round(sig["SL"], 2)
            })
    except Exception as e:
        st.error(f"{symbol} -> {e}")

if results:
    st.subheader("📈 Trade Opportunities Today")
    df_res = pd.DataFrame(results)
    st.dataframe(df_res)
else:
    st.info("No trade setups found today as per strategy.")
