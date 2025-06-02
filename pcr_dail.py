import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

st.set_page_config(page_title="NIFTY vs PCR Trend", layout="centered")
st.title("📊 NIFTY Daily Close vs Put-Call Ratio (Simulated)")

# Fetch last 30 trading days of NIFTY data
nifty = yf.download("^NSEI", period="1mo", interval="1d")
nifty = nifty[["Close"]].dropna().reset_index()
nifty.rename(columns={"Date": "date", "Close": "nifty_close"}, inplace=True)

# Simulate PCR data (in real case, fetch from NSE or data vendor)
np.random.seed(42)
pcr_values = np.round(np.random.uniform(0.8, 1.3, size=len(nifty)), 2)
nifty["pcr"] = pcr_values

# Plot
fig, ax1 = plt.subplots(figsize=(10, 5))

# Nifty line
ax1.set_xlabel("Date")
ax1.set_ylabel("NIFTY Close", color="tab:blue")
ax1.plot(nifty["date"], nifty["nifty_close"], color="tab:blue", label="NIFTY Close")
ax1.tick_params(axis="y", labelcolor="tab:blue")

# PCR on secondary y-axis
ax2 = ax1.twinx()
ax2.set_ylabel("PCR", color="tab:red")
ax2.plot(nifty["date"], nifty["pcr"], color="tab:red", linestyle="--", label="PCR")
ax2.tick_params(axis="y", labelcolor="tab:red")
ax2.axhline(1, color='gray', linestyle='--', linewidth=0.7)

# Title and legend
fig.suptitle("📅 NIFTY Closing Price vs PCR (Simulated for 1 Month)")
fig.tight_layout()
st.pyplot(fig)

# Show data
with st.expander("📋 View Data Table"):
    st.dataframe(nifty)
