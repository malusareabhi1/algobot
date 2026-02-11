# app.py
import streamlit as st
import pandas as pd
from db import fetch_trade_signals, fetch_signal_log, insert_trade_signal, insert_signal_log, create_tables, create_signal_log_table

# -------------------- SETUP --------------------
st.set_page_config(page_title="Algo Trading Dashboard", layout="wide")

# Ensure tables exist
create_tables()
create_signal_log_table()

st.title("📈 Algo Trading Dashboard")

# -------------------- INSERT SIGNAL (optional for testing) --------------------
with st.expander("Insert New Trade Signal (Test)"):
    col1, col2, col3 = st.columns(3)
    with col1:
        opt_type = st.selectbox("Option Type", ["CALL", "PUT"])
        spot = st.number_input("Spot Price", value=18000.0)
        ltp = st.number_input("LTP", value=120.0)
    with col2:
        trending_symbol = st.text_input("Trending Symbol", value="NIFTY")
        expiry = st.text_input("Expiry", value="2026-02-27")
        signal_time = st.text_input("Signal Time", value=pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))

    if st.button("Insert Signal"):
        insert_trade_signal(opt_type, spot, signal_time, trending_symbol, expiry, ltp)
        st.success("✅ Trade Signal Inserted!")

# -------------------- FILTERS --------------------
st.sidebar.header("Filters")
signal_type_filter = st.sidebar.multiselect("Option Type", ["CALL", "PUT"], default=["CALL", "PUT"])
status_filter = st.sidebar.multiselect("Status", ["OPEN", "CLOSED"], default=["OPEN", "CLOSED"])

# -------------------- DISPLAY TRADE SIGNALS --------------------
st.subheader("📊 Trade Signals")
signals_df = pd.DataFrame(fetch_trade_signals(limit=200))
if not signals_df.empty:
    signals_df = signals_df[signals_df['option_type'].isin(signal_type_filter)]
    st.dataframe(signals_df)
else:
    st.info("No trade signals found.")

# -------------------- DISPLAY SIGNAL LOG --------------------
st.subheader("📝 Signal Log")
log_df = fetch_signal_log()
if not log_df.empty:
    log_df = log_df[log_df['status'].isin(status_filter)]
    st.dataframe(log_df)
else:
    st.info("No signal logs found.")

# -------------------- AUTO REFRESH --------------------
st.sidebar.markdown("---")
refresh_interval = st.sidebar.number_input("Refresh Interval (seconds)", min_value=1, value=5)
st.experimental_rerun()
