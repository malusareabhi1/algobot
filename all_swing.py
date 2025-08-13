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

    st_dir = [True] * len(df)
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
    last = df.iloc[-2]  # Yesterday's OHLC
    P = (last['High'] + last['Low'] + last['Close']) / 3
    R1 = 2*P - last['Low']
    S1 = 2*P - last['High']
    R2 = P + (last['High'] - last['Low'])
    S2 = P - (last['High'] - last['Low'])
    return P, R1, S1, R2, S2

def rsi(df, period=14):
    delta = df['Close'].diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(period).mean()
    avg_loss = pd.Series(loss).rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# -------------------
# Signal Logic
# -------------------
def check_signal(df):
    if len(df) < 200:
        return None

    df['EMA200'] = ema(df['Close'], 200)
    df = supertrend(df)
    df['RSI'] = rsi(df)

    P, R1, S1, R2, S2 = pivot_points(df)
    last = df.iloc[-1]
    avg_vol = df['Volume'].rolling(20).mean().iloc[-1]

    # BUY setup
    if last['Close'] > last['EMA200'] and last['ST_Dir'] and last['RSI'] < 70 and last['Volume'] >= avg_vol and last['Close'] > P:
        return {"Signal": "BUY", "Entry": last['Close'], "Target1": R1, "Target2": R2, "Stop Loss": last['Supertrend']}
    
    # SELL setup
    elif last['Close'] < last['EMA200'] and not last['ST_Dir'] and last['RSI'] > 30 and last['Volume'] >= avg_vol and last['Close'] < P:
        return {"Signal": "SELL", "Entry": last['Close'], "Target1": S1, "Target2": S2, "Stop Loss": last['Supertrend']}
    
    return None

# -------------------
# Streamlit App
# -------------------
st.set_page_config(page_title="Bestest 8-Point Swing Scanner", layout="wide")
st.title("📈 NSE Swing Trading Scanner – Bestest 8-Point Strategy")

# Example NIFTY 50 symbols (replace with full list as needed)
nse_symbols = [
    "RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS",
    "SBIN.NS","HINDUNILVR.NS","KOTAKBANK.NS","ITC.NS","LT.NS"
]

start = dt.date.today() - dt.timedelta(days=400)
end = dt.date.today()

results = []

progress_text = "Scanning NSE stocks..."
my_bar = st.progress(0, text=progress_text)

for i, symbol in enumerate(nse_symbols):
    try:
        df = yf.download(symbol, start=start, end=end, interval="1d")
        df.dropna(inplace=True)
        sig = check_signal(df)
        if sig:
            results.append({
                "Stock": symbol.replace(".NS",""),
                "Signal": sig["Signal"],
                "Entry": round(sig["Entry"],2),
                "Target1": round(sig["Target1"],2),
                "Target2": round(sig["Target2"],2),
                "Stop Loss": round(sig["Stop Loss"],2)
            })
    except Exception as e:
        st.error(f"{symbol} -> {e}")
    
    my_bar.progress((i+1)/len(nse_symbols), text=progress_text)

my_bar.empty()

if results:
    st.subheader("📊 High-Probability Swing Setups Today")
    st.dataframe(pd.DataFrame(results))
else:
    st.info("No swing trade setups found today as per strategy.")
