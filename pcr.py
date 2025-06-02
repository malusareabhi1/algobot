import requests
import pandas as pd
import streamlit as st

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

def calculate_pcr(option_data):
    ce_oi = 0  # Call Open Interest
    pe_oi = 0  # Put Open Interest

    for item in option_data:
        if "CE" in item and "PE" in item:
            ce_oi += item["CE"]["openInterest"]
            pe_oi += item["PE"]["openInterest"]

    pcr = round(pe_oi / ce_oi, 2) if ce_oi > 0 else 0
    return pe_oi, ce_oi, pcr

if __name__ == "__main__":
    symbol = "NIFTY"  # Change to "BANKNIFTY" if needed
    try:
        option_chain_data = fetch_nse_option_chain(symbol)
        pe_oi, ce_oi, pcr = calculate_pcr(option_chain_data)

        print(f"Symbol: {symbol}")
        st.write(f"Symbol: {symbol}")
        print(f"Total PUT OI: {pe_oi}")
        st.write(f"Total PUT OI: {pe_oi}")
        print(f"Total CALL OI: {ce_oi}")
        st.write(f"Total CALL OI: {ce_oi}")
        print(f"Put-Call Ratio (PCR): {pcr}")
        st.write(f"Put-Call Ratio (PCR): {pcr}")
    except Exception as e:
        print(f"Error: {e}")
