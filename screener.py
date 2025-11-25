import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt
import plotly.graph_objects as go

st.set_page_config(page_title="Bhanushali Swing Screener", layout="wide")

# -------------------------------
# Helper Functions
# -------------------------------

def rising_ma(ma):
    """Check if 44 MA is rising for last 3 days"""
    return ma.iloc[-1] > ma.iloc[-2] > ma.iloc[-3]


def find_swing_signal(df):
    if len(df) < 50:
        return False

    prev_close = df["Close"].iloc[-2]
    prev_ma44  = df["MA44"].iloc[-2]

    last_close = df["Close"].iloc[-1]
    last_ma44  = df["MA44"].iloc[-1]

    # Example: Bullish swing entry when crossing above MA44
    crossing = (prev_close < prev_ma44) and (last_close > last_ma44)

    return crossing     # ← This now returns only True/False



def plot_chart(df, ticker):
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'], high=df['High'],
        low=df['Low'], close=df['Close'],
        name='Candles'
    ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA44"],
        mode='lines', name='MA44'
    ))

    fig.update_layout(
        title=f"{ticker} – Bhanushali Swing Setup",
        height=500
    )

    return fig


# -------------------------------
# UI
# -------------------------------

st.title("📈 Bhanushali Swing Stock Screener")
st.write("44 MA Rising + Crossing Candle + Support Logic")

nifty100 = [
"RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","ICICIBANK.NS","KOTAKBANK.NS",
"SBIN.NS","AXISBANK.NS","LT.NS","ITC.NS","HINDUNILVR.NS","WIPRO.NS","HCLTECH.NS",
"MARUTI.NS","BAJAJFINSV.NS","BAJFINANCE.NS","ULTRACEMCO.NS","NESTLEIND.NS",
"ADANIENT.NS","ADANIPORTS.NS","JSWSTEEL.NS","TATASTEEL.NS","POWERGRID.NS",
"BHARTIARTL.NS","ONGC.NS","COALINDIA.NS","BRITANNIA.NS","CIPLA.NS","DIVISLAB.NS",
"EICHERMOT.NS","TATAMOTORS.NS","HDFCLIFE.NS","ICICIPRULI.NS","BAJAJ-AUTO.NS",
"HEROMOTOCO.NS","ASIANPAINT.NS","SUNPHARMA.NS","DRREDDY.NS","GRASIM.NS",
"SHREECEM.NS","HINDZINC.NS","TITAN.NS","INDUSINDBK.NS","M&M.NS","BPCL.NS",
"IOC.NS","GAIL.NS","VEDL.NS","DLF.NS","ABB.NS"
]  # add more if needed

results = []

st.info("Fetching data... (may take 10–20 seconds)")

for ticker in nifty100:
    df = yf.download(ticker, period="6mo", interval="1d")
    if df.empty:
        continue

    if find_swing_signal(df):
        last = df.iloc[-1]
        results.append({
            "Stock": ticker.replace(".NS", ""),
            "Close": round(last["Close"], 2),
            "Buy Above": round(last["High"], 2),
            "Stoploss": round(last["Low"], 2),
            "Target 1 (1:2)": round(last["High"] + 2*(last["High"] - last["Low"]), 2),
            "Target 2 (1:3)": round(last["High"] + 3*(last["High"] - last["Low"]), 2)
        })

df_results = pd.DataFrame(results)

st.subheader("📊 Screener Results")

if df_results.empty:
    st.warning("No stocks match the Bhanushali Swing Setup today.")
else:
    st.dataframe(df_results)

    csv = df_results.to_csv(index=False)
    st.download_button("📥 Download CSV", csv, "bhanushali_screener.csv")

    # Chart section
    st.subheader("📈 Chart Viewer")
    selected = st.selectbox("Select stock", df_results["Stock"].tolist())

    df_chart = yf.download(selected + ".NS", period="6mo", interval="1d")
    df_chart["MA44"] = df_chart["Close"].rolling(44).mean()

    st.plotly_chart(plot_chart(df_chart, selected), use_container_width=True)
