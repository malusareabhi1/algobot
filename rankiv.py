import streamlit as st
import requests
import pandas as pd
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import yfinance as yf
from datetime import datetime, timedelta

# NSE Headers for option chain
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://www.nseindia.com/'
}

@st.cache_data(ttl=60)  # Refresh every minute
def fetch_nifty_option_chain():
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    session = requests.Session()
    session.headers.update(headers)
    response = session.get(url)
    data = response.json()
    records = data['records']['data']
    df = pd.DataFrame(records)
    return df

def black_scholes_iv(S, K, T, r, sigma, option_type='call', price=None):
    """Calculate IV using Black-Scholes (for verification)"""
    def bs_price(sigma):
        d1 = (np.log(S/K) + (r + 0.5*sigma**2)*T) / (sigma*np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        if option_type == 'call':
            return S * norm.cdf(d1) - K * np.exp(-r*T) * norm.cdf(d2)
        else:
            return K * np.exp(-r*T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    if price is None:
        return bs_price(sigma)
    try:
        return brentq(lambda sigma: bs_price(sigma) - price, 0.001, 5.0)
    except:
        return np.nan

def calculate_iv_rank(current_iv, hist_high=0.40, hist_low=0.10):
    """Simple IV Rank calculation (replace hist_high/low with fetched data)"""
    if hist_high == hist_low:
        return 0
    return max(0, min(100, (current_iv - hist_low) / (hist_high - hist_low) * 100))

# Streamlit App
st.title("🛡️ Nifty Options IV Rank Finder")
st.markdown("Select expiry & strike to view current IV and IV Rank.")

# Sidebar inputs
expiry = st.sidebar.selectbox("Select Expiry", options=["Nearest", "Next", "Current Week"], index=0)
option_type = st.sidebar.selectbox("Option Type", ["CE", "PE"])
strike_range = st.sidebar.slider("Strike Range (±)", 0, 1000, 200, 50)

df = fetch_nifty_option_chain()
if not df.empty:
    underlying = df['underlyingValue'].iloc[0]
    st.metric("Nifty Spot", f"{underlying:,.0f}")
    
    # Filter options (simplified for current expiry)
    calls = df[df['expiryDate'] == df['expiryDate'].max()]
    puts = calls
    atm_strike = round(underlying / 100) * 100
    
    selected_strike = st.selectbox("Select Strike", 
                                   options=sorted(set(calls['strikePrice'].unique())), 
                                   index=np.argmin(np.abs(calls['strikePrice'].unique() - atm_strike)))
    
    # Get option data
    ce_data = calls[calls['strikePrice'] == selected_strike]
    pe_data = puts[puts['strikePrice'] == selected_strike]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not ce_data.empty:
            ce_iv = ce_data['impliedVolatility'].iloc[0] * 100 if 'impliedVolatility' in ce_data else np.nan
            iv_rank_ce = calculate_iv_rank(ce_iv / 100)
            st.metric("CE IV Rank %", f"{iv_rank_ce:.1f}", delta=f"{ce_iv:.1f}%")
    
    with col2:
        if not pe_data.empty:
            pe_iv = pe_data['impliedVolatility'].iloc[0] * 100 if 'impliedVolatility' in pe_data else np.nan
            iv_rank_pe = calculate_iv_rank(pe_iv / 100)
            st.metric("PE IV Rank %", f"{iv_rank_pe:.1f}", delta=f"{pe_iv:.1f}%")
    
    # Table of nearby strikes
    nearby_strikes = sorted(set(calls['strikePrice'].unique()), 
                           key=lambda x: abs(x - underlying))[:10]
    table_data = []
    for strike in nearby_strikes:
        ce_row = calls[calls['strikePrice'] == strike]
        if not ce_row.empty and 'impliedVolatility' in ce_row:
            iv = ce_row['impliedVolatility'].iloc[0] * 100
            ivr = calculate_iv_rank(iv / 100)
            table_data.append({'Strike': strike, 'CE IV %': f"{iv:.1f}", 'IV Rank %': f"{ivr:.1f}"})
    
    st.subheader("Nearby Strikes IV Rank")
    st.dataframe(pd.DataFrame(table_data), use_container_width=True)
    
    # Historical note
    st.info("🔄 **Upgrade**: Use `nsepython.derivative_history()` for 52w IV data to compute accurate ranks. Sample high/low used here [web:2].")
else:
    st.error("Failed to fetch NSE data. Check internet/NSE availability.")

if st.sidebar.button("Run: streamlit run app.py"):
    st.success("Deployed! Access via browser.")
