import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

# =====================================================
# 44 MA + 200 MA Strategy
# =====================================================

def compute_signal(df, risk_rr=3.0):
    df = df.copy()

    # Ensure we have the right columns
    expected = {"Date", "Open", "High", "Low", "Close"}
    if not expected.issubset(df.columns):
        return None

    df = df.sort_values("Date").reset_index(drop=True)

    df["MA44"] = df["Close"].rolling(44).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    df["trend_up"] = (
        (df["Close"] > df["MA200"]) &
        (df["MA44"] > df["MA200"]) &
        (df["MA44"] > df["MA44"].shift(1))
    )

    if len(df) < 201:
        return None

    today = df.iloc[-1]
    prev = df.iloc[-2]

    if not bool(today["trend_up"]):
        return None

    touch_44 = prev["Low"] <= prev["MA44"] <= prev["High"]
    breakout = today["High"] > prev["High"] and today["Close"] > prev["High"]

    if not (touch_44 and breakout):
        return None

    entry = float(today["High"])
    sl = float(prev["Low"])
    risk = entry - sl
    if risk <= 0:
        return None

    target = entry + risk * risk_rr

    return {
        "Entry Date": today["Date"].date(),
        "Entry": round(entry, 2),
        "Stop Loss": round(sl, 2),
        "Target": round(target, 2),
        "RR": risk_rr,
    }

# =====================================================
# Streamlit App
# =====================================================

st.set_page_config(layout="wide")
st.title("📈 44 MA + 200 MA Swing Scanner (Auto Data Download)")

st.markdown("""
**Upload a CSV with stock symbols only.  
The app will automatically download daily data and scan for signals.**
""")

uploaded_file = st.file_uploader(
    "Upload Stock List CSV (Column name: Symbol)",
    type=["csv"]
)

risk_rr = st.number_input(
    "Reward : Risk",
    value=3.0,
    min_value=1.0,
    step=0.5
)

if uploaded_file:
    stock_list = pd.read_csv(uploaded_file)

    if "Symbol" not in stock_list.columns:
        st.error("CSV must contain a column named 'Symbol'")
    else:
        if st.button("🔍 Scan Stocks"):
            results = []

            with st.spinner("Downloading data & scanning..."):
                for symbol in stock_list["Symbol"]:
                    try:
                        df = yf.download(
                            symbol,
                            period="6mo",
                            interval="1d",
                            progress=False
                        )

                        if df.empty:
                            continue

                        df = df.reset_index()
                        df = df.rename(columns={
                            "Open": "Open",
                            "High": "High",
                            "Low": "Low",
                            "Close": "Close",
                            "Date": "Date"
                        })

                        signal = compute_signal(df, risk_rr)

                        if signal:
                            results.append({
                                "Symbol": symbol,
                                **signal
                            })

                    except Exception as e:
                        st.warning(f"{symbol}: {e}")

            result_df = pd.DataFrame(results)

            st.subheader("✅ Stocks with ACTIVE BUY Signal")

            if result_df.empty:
                st.warning("No stocks satisfy the strategy today.")
            else:
                st.dataframe(result_df, use_container_width=True)

                csv = result_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Signals",
                    csv,
                    "44MA_Signals.csv",
                    "text/csv"
                )

st.markdown("---")
st.markdown("Daily swing scanner using 44 MA pullback + breakout logic")
