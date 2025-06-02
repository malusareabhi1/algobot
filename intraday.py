import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import ta

st.set_page_config(page_title="NIFTY 200 Intraday Scanner", layout="wide")
st.title("📈 NIFTY 200 Intraday Buy/Sell Scanner")

# Sample subset from NIFTY 200
nifty200_stocks = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "AXISBANK.NS", "ITC.NS", "LT.NS", "HINDUNILVR.NS"
]

strategy = st.radio("Select Strategy", ["EMA44 Breakout", "Price + Volume Spike"])

scan_button = st.button("🔍 Scan Now")

if scan_button:
    results = []

    with st.spinner("Scanning stocks..."):
        for stock in nifty200_stocks:
            try:
                df = yf.download(stock, interval="5m", period="1d", progress=False)
                df.dropna(inplace=True)
                if len(df) < 50:
                    continue

                df["EMA44"] = ta.trend.ema_indicator(df["Close"], window=44)
                df["Vol_Avg"] = df["Volume"].rolling(20).mean()
                df["Return"] = df["Close"].pct_change()

                last = df.iloc[-1]
                prev = df.iloc[-2]

                # EMA44 Breakout Logic
                if strategy == "EMA44 Breakout":
                    if prev["Close"] < prev["EMA44"] and last["Close"] > last["EMA44"]:
                        results.append({
                            "Stock": stock,
                            "Signal": "BUY",
                            "Entry": round(last["Close"], 2),
                            "Stoploss": round(last["EMA44"], 2),
                            "Target": round(last["Close"] * 1.01, 2)
                        })
                    elif prev["Close"] > prev["EMA44"] and last["Close"] < last["EMA44"]:
                        results.append({
                            "Stock": stock,
                            "Signal": "SELL",
                            "Entry": round(last["Close"], 2),
                            "Stoploss": round(last["EMA44"], 2),
                            "Target": round(last["Close"] * 0.99, 2)
                        })

                # Price + Volume Spike Logic
                elif strategy == "Price + Volume Spike":
                    last3 = df.tail(3)
                    price_change = (last3["Close"].iloc[-1] - last3["Close"].iloc[0]) / last3["Close"].iloc[0]
                    vol_spike = last["Volume"] > 1.5 * last["Vol_Avg"]
                    if price_change > 0.005 and vol_spike:
                        results.append({
                            "Stock": stock,
                            "Signal": "BUY",
                            "Entry": round(last["Close"], 2),
                            "Stoploss": round(last["Close"] * 0.995, 2),
                            "Target": round(last["Close"] * 1.01, 2)
                        })
                    elif price_change < -0.005 and vol_spike:
                        results.append({
                            "Stock": stock,
                            "Signal": "SELL",
                            "Entry": round(last["Close"], 2),
                            "Stoploss": round(last["Close"] * 1.005, 2),
                            "Target": round(last["Close"] * 0.99, 2)
                        })
            except Exception as e:
                st.warning(f"Error with {stock}: {e}")

    if results:
        df_results = pd.DataFrame(results)
        st.success(f"Signals Found: {len(df_results)}")
        st.dataframe(df_results)
    else:
        st.info("No trading signals found with selected strategy.")

