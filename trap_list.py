import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config("🪤 Multi-Stock TRAP Strategy", layout="wide")
st.title("🪤 TRAP Strategy on Multiple NSE Stocks")

# NSE Example symbols
nse_stocks = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "LT.NS", "AXISBANK.NS", "WIPRO.NS"
]

selected_symbols = st.sidebar.multiselect("📌 Select NSE Stocks", nse_stocks, default=["RELIANCE.NS"])
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("2025-06-10"))

@st.cache_data
def fetch_data(symbol, start, end):
    df = yf.download(symbol, start=start, end=end)
    df.dropna(inplace=True)
    return df

def detect_trap_signals(df):
    df['20High'] = df['High'].rolling(20).max()
    df['20Low'] = df['Low'].rolling(20).min()
    traps = []

    for i in range(21, len(df)-1):
        try:
            today_high = df['High'].iloc[i]
            today_low = df['Low'].iloc[i]
            today_close = df['Close'].iloc[i]
            prior_20high = df['20High'].iloc[i-1]
            prior_20low = df['20Low'].iloc[i-1]
            next_close = df['Close'].iloc[i+1]
            next_date = df.index[i+1]

            if today_high > prior_20high and next_close < today_close:
                traps.append((next_date, next_close, 'SELL TRAP'))

            elif today_low < prior_20low and next_close > today_close:
                traps.append((next_date, next_close, 'BUY TRAP'))
        except:
            continue

    return pd.DataFrame(traps, columns=["Date", "Price", "Signal"]).set_index("Date")

# Result table
all_signals = []

for symbol in selected_symbols:
    df = fetch_data(symbol, start_date, end_date)
    traps = detect_trap_signals(df)
    if not traps.empty:
        traps["Symbol"] = symbol
        all_signals.append(traps)

if all_signals:
    final_df = pd.concat(all_signals).sort_index()
    st.subheader("📋 TRAP Signals Across Stocks")
    st.dataframe(final_df)
else:
    st.info("No TRAP signals found in the selected date range across selected stocks.")
