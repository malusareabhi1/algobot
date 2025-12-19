import streamlit as st
import pandas as pd
import numpy as np
import os

# =====================================================
# 44 MA + 200 MA Swing Strategy (Scanner Version)
# =====================================================


def compute_ma_signals(df, risk_rr=3.0):
    """
    Apply Siddharth-style 44 MA + 200 MA swing logic on OHLC data
    Returns dataframe and trades dataframe
    """
    df = df.copy()

    # Normalize column names
    rename_map = {}
    for col in df.columns:
        lc = col.lower()
        if lc.startswith("date") or lc.startswith("time"):
            rename_map[col] = "Date"
        elif lc.startswith("open"):
            rename_map[col] = "Open"
        elif lc.startswith("high"):
            rename_map[col] = "High"
        elif lc.startswith("low"):
            rename_map[col] = "Low"
        elif lc.startswith("close"):
            rename_map[col] = "Close"

    df = df.rename(columns=rename_map)

    if "Date" not in df.columns:
        raise ValueError("Date column missing")

    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    # Moving Averages
    df["MA44"] = df["Close"].rolling(44).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    # Trend filter
    df["trend_up"] = (
        (df["Close"] > df["MA200"]) &
        (df["MA44"] > df["MA200"]) &
        (df["MA44"] > df["MA44"].shift(1))
    )

    trades = []
    in_trade = False

    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]

        if np.isnan(row["MA44"]) or np.isnan(row["MA200"]):
            continue

        if in_trade:
            continue

        if not row["trend_up"]:
            continue

        # Pullback + breakout condition
        touch_44 = prev["Low"] <= prev["MA44"] <= prev["High"]
        breakout = row["High"] > prev["High"] and row["Close"] > prev["High"]

        if touch_44 and breakout:
            entry = row["High"]
            sl = prev["Low"]
            risk = entry - sl

            if risk <= 0:
                continue

            target = entry + risk * risk_rr

            trades.append({
                "entry_date": row["Date"],
                "entry_price": entry,
                "sl": sl,
                "target": target,
                "risk": risk,
                "RR": risk_rr
            })

            in_trade = True

    return df, pd.DataFrame(trades)


# =====================================================
# Check if latest candle gives signal
# =====================================================

def is_latest_signal(df):
    df, trades = compute_ma_signals(df)

    if trades.empty:
        return False, None

    last_trade = trades.iloc[-1]
    last_date = df.iloc[-1]["Date"]

    if last_trade["entry_date"].date() == last_date.date():
        return True, last_trade

    return False, None


# =====================================================
# Streamlit App
# =====================================================

st.set_page_config(layout="wide")
st.title("📈 44 MA + 200 MA Swing Scanner (Multi-Stock)")

st.markdown(
    """
    **What this app does**
    - Reads multiple stock CSV files
    - Applies 44 MA pullback + breakout strategy
    - Lists ONLY stocks where condition is TRUE on latest candle
    """
)

st.subheader("1️⃣ Upload Stock List CSV")

stock_list_file = st.file_uploader(
    "CSV must contain: Symbol, FilePath",
    type=["csv"]
)

risk_rr = st.number_input(
    "Reward : Risk",
    value=3.0,
    min_value=1.0,
    step=0.5
)

if stock_list_file:
    stock_list = pd.read_csv(stock_list_file)

    required_cols = {"Symbol", "FilePath"}
    if not required_cols.issubset(stock_list.columns):
        st.error("CSV must contain Symbol and FilePath columns")
    else:
        if st.button("🔍 Scan Stocks"):
            results = []

            with st.spinner("Scanning stocks..."):
                for _, row in stock_list.iterrows():
                    symbol = row["Symbol"]
                    path = row["FilePath"]

                    if not os.path.exists(path):
                        continue

                    try:
                        df = pd.read_csv(path)
                        signal, trade = is_latest_signal(df)

                        if signal:
                            results.append({
                                "Symbol": symbol,
                                "Entry Date": trade["entry_date"],
                                "Entry": round(trade["entry_price"], 2),
                                "Stop Loss": round(trade["sl"], 2),
                                "Target": round(trade["target"], 2),
                                "RR": trade["RR"]
                            })

                    except Exception as e:
                        st.warning(f"{symbol}: {e}")

            result_df = pd.DataFrame(results)

            st.subheader("📊 Stocks with ACTIVE BUY Signal")

            if result_df.empty:
                st.warning("No stock satisfies the strategy today")
            else:
                st.dataframe(result_df, use_container_width=True)

                csv = result_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Signals",
                    csv,
                    "44MA_signals.csv",
                    "text/csv"
                )

st.markdown("---")
st.markdown("Built for swing trading education & scanning purposes")
