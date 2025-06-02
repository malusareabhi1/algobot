import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

# Function to fetch live option chain data
@st.cache_data(ttl=300)
def fetch_nse_option_chain(symbol="NIFTY"):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)  # Set cookies
    response = session.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception("Failed to fetch data from NSE")
    data = response.json()
    return data["records"]["data"]

# Function to calculate PCR
def calculate_pcr(option_data):
    ce_oi = 0
    pe_oi = 0
    pcr_data = []

    for item in option_data:
        strike = item.get("strikePrice")
        ce_oi_val = item.get("CE", {}).get("openInterest", 0)
        pe_oi_val = item.get("PE", {}).get("openInterest", 0)
        ce_oi += ce_oi_val
        pe_oi += pe_oi_val
        if ce_oi_val and pe_oi_val:
            pcr_data.append((strike, round(pe_oi_val / ce_oi_val, 2)))

    total_pcr = round(pe_oi / ce_oi, 2) if ce_oi > 0 else 0
    return pe_oi, ce_oi, total_pcr, pcr_data

# Streamlit UI
st.set_page_config(page_title="Put Call Ratio (PCR) - NSE", layout="centered")
st.title("📈 Put-Call Ratio (PCR) Live Dashboard")

symbol = st.selectbox("Select Index", ["NIFTY", "BANKNIFTY"])
try:
    option_data = fetch_nse_option_chain(symbol)
    pe_oi, ce_oi, total_pcr, pcr_list = calculate_pcr(option_data)

    st.markdown(f"""
    **Symbol**: `{symbol}`  
    **Total PUT OI**: `{pe_oi}`  
    **Total CALL OI**: `{ce_oi}`  
    **Put-Call Ratio (PCR)**: `📊 {total_pcr}`
    """)

    # Create PCR vs Strike Price Plot
    if pcr_list:
        strikes, pcr_values = zip(*pcr_list)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(strikes, pcr_values, marker='o', linestyle='-')
        ax.axhline(1, color='red', linestyle='--', label='PCR = 1')
        ax.set_title(f"{symbol} PCR by Strike Price")
        ax.set_xlabel("Strike Price")
        ax.set_ylabel("PCR (PE OI / CE OI)")
        ax.grid(True)
        ax.legend()
        st.pyplot(fig)
except Exception as e:
    st.error(f"Error fetching data: {e}")
