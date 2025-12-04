import streamlit as st
import pandas as pd
import numpy as np
from nsepython import nse_optionchain  # Reliable NSE wrapper
from datetime import datetime, timedelta
import time

@st.cache_data(ttl=120)  # Cache 2 mins
def fetch_nifty_chain():
    """Fetch using nsepython - handles NSE anti-bot automatically"""
    try:
        data = nse_optionchain("NIFTY")
        if data and 'records' in data and 'data' in data['records']:
            df = pd.json_normalize(data['records']['data'])
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"NSE fetch failed: {str(e)}. Using fallback.")
        return pd.DataFrame()

def calculate_iv_rank(iv_current, iv_high=0.45, iv_low=0.08):
    """IV Rank: (current - low) / (high - low) * 100"""
    if iv_high <= iv_low:
        return 0
    return max(0, min(100, (iv_current - iv_low) / (iv_high - iv_low) * 100))

# Streamlit App
st.title("🛡️ Nifty Options IV Rank Dashboard")
st.markdown("**Live NSE data** - Select strike/expiry for IV analysis.")

# Fetch data
with st.spinner("Fetching live Nifty option chain..."):
    df = fetch_nifty_chain()
    
if df.empty:
    st.warning("⚠️ No live data. Market closed? Try during 9:15-15:30 IST.")
    st.stop()

# Key metrics
underlying = float(df['underlyingValue'].iloc[0])
st.metric("Nifty Spot", f"{underlying:,.0f}")

# Controls
col1, col2 = st.columns(2)
with col1:
    option_type = st.selectbox("Type", ["CE", "PE"], index=0)
with col2:
    strike_offset = st.slider("Strike Offset", -500, 500, 0, 50)

# Find nearest expiry & ATM strike
expiries = df['expiryDate'].unique()
current_expiry = sorted(expiries)[0]  # Nearest expiry
atm_strike = round(underlying / 100) * 100
selected_strike = atm_strike + strike_offset

# Filter data
target_row = df[(df['strikePrice'] == selected_strike) & 
                (df['expiryDate'] == current_expiry) &
                (df[option_type] == df[option_type].first_valid_index())]

if not target_row.empty:
    row = target_row.iloc[0]
    iv_raw = row.get(f"{option_type}.impliedVolatility", np.nan)
    iv_pct = iv_raw * 100 if pd.notna(iv_raw) else np.nan
    
    iv_rank = calculate_iv_rank(iv_raw) if pd.notna(iv_raw) else 0
    
    st.metric(f"{option_type} IV", f"{iv_pct:.1f}%" if pd.notna(iv_pct) else "N/A")
    st.metric("IV Rank %", f"{iv_rank:.1f}", 
              delta=f"High >50% = Sell premium" if iv_rank > 50 else "Low <30% = Buy premium")
    
    # Greeks
    st.json({
        "Delta": row.get(f"{option_type}.delta", "N/A"),
        "Gamma": row.get(f"{option_type}.gamma", "N/A"),
        "Theta": row.get(f"{option_type}.theta", "N/A"),
        "Vega": row.get(f"{option_type}.vega", "N/A")
    })
else:
    st.warning(f"No data for {option_type} {selected_strike} on {current_expiry}")

# Nearby strikes table
st.subheader("Nearby Strikes IV Rank Table")
nearby_strikes = sorted(df['strikePrice'].unique(), 
                       key=lambda x: abs(x - underlying))[:15]

table_data = []
for strike in nearby_strikes:
    for opt_type in ['CE', 'PE']:
        row = df[(df['strikePrice'] == strike) & 
                (df['expiryDate'] == current_expiry) & 
                (df[opt_type].notna())]
        if not row.empty:
            iv_raw = row.iloc[0][f"{opt_type}.impliedVolatility"]
            iv_pct = iv_raw * 100
            ivr = calculate_iv_rank(iv_raw)
            table_data.append({
                'Strike': strike,
                'Type': opt_type,
                'IV %': f"{iv_pct:.1f}",
                'IV Rank': f"{ivr:.1f}%",
                'OI': f"{row.iloc[0][f'{opt_type}.openInterest']:,.0f}"
            })

if table_data:
    df_table = pd.DataFrame(table_data)
    st.dataframe(df_table, use_container_width=True, height=400)
else:
    st.info("No option data available.")

# Footer
st.info("""
**Notes**: 
- Uses `nsepython` for reliable NSE data [web:28]
- IV Rank uses sample 52w range (8-45%). Fetch historical via `nsepython.bhavcopy_daily()` for accuracy
- For Zerodha: Replace with `kite.quote()` + `kite.historical_data()` [web:30]
- Run: `streamlit run rankiv_fixed.py`
""")
