import streamlit as st
from strategies import doctor_strategy
from utils import telegram_alert, trade_logger
from broker import zerodha_api

st.set_page_config(layout="wide", page_title="Algo Trading MVP")

st.sidebar.title("Doctor Algo")
menu = st.sidebar.selectbox("Select Action", ["Backtest", "Live Trade", "Trade Logs"])

if menu == "Backtest":
    st.header("📊 Strategy Backtest")
    uploaded_file = st.file_uploader("Upload historical data (CSV)", type=["csv"])
    if uploaded_file:
        df = doctor_strategy.load_data(uploaded_file)
        results = doctor_strategy.run_backtest(df)
        st.write(results["metrics"])
        st.pyplot(results["chart"])

elif menu == "Live Trade":
    st.header("⚡ Live Trading (Paper/Real)")
    if st.button("Start Doctor Strategy"):
        st.success("Running Doctor Strategy in background...")
        doctor_strategy.run_live_trade()

elif menu == "Trade Logs":
    st.header("📋 Trade Logs")
    trade_logger.show_logs()
