import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
from datetime import datetime
import time

@st.cache_data(ttl=120)
def fetch_nifty_option_chain():
    """Direct NSE API with proper headers - works Dec 2025"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    })
    
    # Step 1: Get NSE cookies first
    session.get('https://www.nseindia.com/', timeout=10)
    
    # Step 2: Get option chain
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    try:
        response = session.get(url, timeout=15)
        
        # Check if response is HTML (NSE blocked)
        if not response.headers.get('content-type', '').startswith('application/json'):
            return pd.DataFrame()
        
        data = response.json()
        if 'records' not in data or 'data' not in data['records']:
            return pd.DataFrame()
            
        # Flatten nested JSON
        records = []
        for item in data['records']['data']:
            flat_row = {}
            flat_row.update(item)
            
            # Flatten CE and PE data
            if item.get('CE'):
                for key, val in item['CE'].items():
                    flat_row[f'CE.{key}'] = val
            if item.get('PE'):
                for key, val in item['PE'].items():
                    flat_row[f'PE.{key}'] = val
                    
            records.append(flat_row)
            
        df = pd.DataFrame(records)
        return df
    except Exception as e:
        st.error(f"NSE API error: {str(e)}")
        return pd.DataFrame()

def calculate_iv_rank(iv_current, iv_high=0.45, iv_low=0.08):
    """IV Rank calculation"""
    if pd.isna(iv_current) or iv_high <= iv_low:
        return 0
    return max(0, min(100, (iv_current - iv_low) / (iv_high - iv_low) * 100))

# === STREAMLIT APP ===
st.set_page_config(page_title="Nifty IV Rank", layout="wide")
st.title("🛡️ Nifty Options IV Rank Finder")
st.markdown("**Live NSE data** - No external libraries needed")

# Fetch data with spinner
with st.spinner("🔄 Fetching live Nifty option chain..."):
    df = fetch_nifty_option_chain()
    time.sleep(1)  # Let user see spinner

if df.empty:
    st.warning("⚠️ **Market Closed** (10 PM IST) or NSE blocking. Try 9:15-15:30 IST.")
    st.info("**Test Data**: Using sample IV for demo...")
    
    # Sample data for testing
    df = pd.DataFrame({
        'strikePrice': [25900, 25950, 26000, 26050],
        'expiryDate': ['04-Dec-25']*4,
        'underlyingValue': [25900]*4,
        'CE.impliedVolatility': [0.18, 0.22, 0.25, 0.19],
        'PE.impliedVolatility': [0.20, 0.23, 0.21, 0.24],
        'CE.openInterest': [50000, 45000, 40000, 35000],
        'PE.openInterest': [55000, 48000, 42000, 38000]
    })
else:
    st.success(f"✅ Live data loaded: {len(df)} strikes")

# Key metrics
if not df.empty:
    underlying = df['underlyingValue'].iloc[0] if 'underlyingValue' in df.columns else 24150
    st.metric("Nifty Spot", f"{underlying:,.0f}")

# Controls
col1, col2, col3 = st.columns(3)
with col1:
    opt_type = st.selectbox("Option", ["CE", "PE"])
with col2:
    strike_offset = st.slider("Offset from ATM", -300, 300, 0, 50)
with col3:
    atm_strike = round(underlying / 100) * 100
    selected_strike = atm_strike + strike_offset
    st.metric("Selected Strike", selected_strike)

# Find data for selected strike
iv_cols = [col for col in df.columns if col.startswith(f'{opt_type}.impliedVolatility')]
if iv_cols and not df.empty:
    df[opt_type + '_IV'] = df[iv_cols[0]].fillna(0) if iv_cols else 0
    
    selected_row = df[df['strikePrice'] == selected_strike]
    if not selected_row.empty:
        iv_raw = selected_row[opt_type + '_IV'].iloc[0]
        iv_pct = iv_raw * 100
        iv_rank = calculate_iv_rank(iv_raw)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(f"{opt_type} IV", f"{iv_pct:.1f}%")
        with col2:
            st.metric("IV Rank", f"{iv_rank:.1f}%", 
                     delta="🔴 Sell Premium" if iv_rank > 50 else "🟢 Buy Premium")
    else:
        st.warning(f"No data for strike {selected_strike}")

# IV Rank Table - Top 10 ATM strikes
st.subheader("📊 Nearby Strikes IV Rank")
if not df.empty:
    atm_strikes = sorted(df['strikePrice'].unique(), 
                        key=lambda x: abs(x - underlying))[:10]
    
    table_data = []
    for strike in atm_strikes:
        row = df[df['strikePrice'] == strike].iloc[0] if len(df[df['strikePrice'] == strike]) > 0 else None
        
        if row is not None:
            for opt in ['CE', 'PE']:
                iv_raw = row.get(f'{opt}.impliedVolatility', np.nan)
                if pd.notna(iv_raw):
                    iv_pct = iv_raw * 100
                    ivr = calculate_iv_rank(iv_raw)
                    oi = row.get(f'{opt}.openInterest', 0)
                    
                    table_data.append({
                        'Strike': strike,
                        'Type': opt,
                        'IV %': f"{iv_pct:.1f}",
                        f'IV Rank': f"{ivr:.1f}%",
                        'OI': f"{oi:,.0f}"
                    })
    
    if table_data:
        df_table = pd.DataFrame(table_data)
        st.dataframe(df_table, use_container_width=True, height=300)
    else:
        st.info("No IV data available")

# Instructions
with st.expander("🚀 Deploy Instructions"):
    st.code("""
    1. Save as rankiv_v3.py
    2. pip install streamlit pandas numpy requests
    3. streamlit run rankiv_v3.py
    4. Works on Streamlit Cloud / Local
    """)

st.info("**Pro Tip**: High IV Rank (>50%) = Sell options. Low (<30%) = Buy options [web:7]")
