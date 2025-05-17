import pandas as pd
import streamlit as st
import os

log_file = "trade_logs/logs.csv"

def log_trade(entry):
    df = pd.DataFrame([entry])
    if not os.path.exists(log_file):
        df.to_csv(log_file, index=False)
    else:
        df.to_csv(log_file, mode="a", header=False, index=False)

def show_logs():
    if os.path.exists(log_file):
        df = pd.read_csv(log_file)
        st.dataframe(df)
    else:
        st.info("No trade logs found.")
