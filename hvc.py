import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="HVC Swing Scanner", layout="wide")

st.title("📊 HVC (Highest Volume Candle) Swing Scanner")

# -------------------------
# User Inputs
# -------------------------
lookback = st.sidebar.slider("HVC Lookback (days)", 10, 40, 20)
vol_multiplier = st.sidebar.slider("Volume Multiplier", 1.0, 3.0, 1.5)

symbols = st.sidebar.text_area(
    "NSE Symbols (comma separated)",
    """RELIANCE.NS,TCS.NS,HDFCBANK.NS,ICICIBANK.NS,INFY.NS,SBIN.NS,LT.NS,
    ITC.NS,HINDUNILVR.NS,AXISBANK.NS,KOTAKBANK.NS,BAJFINANCE.NS,
    BHARTIARTL.NS,ASIANPAINT.NS,HCLTECH.NS,MARUTI.NS,SUNPHARMA.NS,
    TITAN.NS,ULTRACEMCO.NS,NTPC.NS,POWERGRID.NS,TATASTEEL.NS,
    ONGC.NS,JSWSTEEL.NS,TECHM.NS,INDUSINDBK.NS,ADANIPORTS.NS,
    DIVISLAB.NS,CIPLA.NS,DRREDDY.NS,EICHERMOT.NS,GRASIM.NS,
    HDFCLIFE.NS,HEROMOTOCO.NS,HINDALCO.NS,ICICIPRULI.NS,
    LTIM.NS,M&M.NS,NESTLEIND.NS,SBILIFE.NS,TATACONSUM.NS,
    TATAMOTORS.NS,UPL.NS,WIPRO.NS,BAJAJFINSV.NS"""
    )


symbols = [s.strip() + ".NS" for s in symbols.split(",") if s.strip()]

# -------------------------
# HVC Logic
# -------------------------
def detect_hvc(df, lookback, vol_multiplier):
    recent = df.tail(lookback)

    hvc_idx = recent['Volume'].idxmax()
    hvc = df.loc[hvc_idx]

    avg_vol = recent['Volume'].mean()

    if hvc['Volume'] < vol_multiplier * avg_vol:
        return None

    signal = "WAIT"

    if df.iloc[-1]['Close'] > hvc['High']:
        signal = "BUY"
    elif df.iloc[-1]['Close'] < hvc['Low']:
        signal = "SELL"

    return {
        "HVC Date": hvc_idx.date(),
        "HVC High": round(hvc['High'], 2),
        "HVC Low": round(hvc['Low'], 2),
        "HVC Volume": int(hvc['Volume']),
        "Close": round(df.iloc[-1]['Close'], 2),
        "Signal": signal,
        "Stoploss": round(hvc['Low'], 2) if signal == "BUY" else round(hvc['High'], 2)
    }

# -------------------------
# Scan Button
# -------------------------
if st.button("🔎 Scan HVC"):

    results = []

    for sym in symbols:
        try:
            df = yf.download(sym, period="2mo", interval="1d", progress=False)

            if len(df) < lookback:
                continue

            hvc_data = detect_hvc(df, lookback, vol_multiplier)

            if hvc_data:
                hvc_data["Symbol"] = sym.replace(".NS", "")
                results.append(hvc_data)

        except Exception as e:
            st.warning(f"Error fetching {sym}")

    if results:
        result_df = pd.DataFrame(results)
        st.success(f"Found {len(result_df)} HVC setups")
        st.dataframe(result_df, use_container_width=True)
    else:
        st.warning("No HVC setups found")
