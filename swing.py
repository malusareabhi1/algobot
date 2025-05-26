import streamlit as st
import yfinance as yf
import pandas as pd

# Title
st.title("📈 Swing Trade Stock Screener (NIFTY 100)")

# Sidebar options
sma_period = st.sidebar.slider("SMA Period", min_value=20, max_value=100, value=44)
volume_lookback = st.sidebar.slider("Volume Avg Period", min_value=5, max_value=20, value=10)

# Sample NIFTY 100 stock list (shortened, you can replace with full list)
nifty_100 = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'LT', 'AXISBANK',
    'KOTAKBANK', 'HCLTECH', 'WIPRO', 'ITC', 'ULTRACEMCO', 'BAJFINANCE', 'ASIANPAINT'
]
nifty_100 = [
    'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
    'KOTAKBANK.NS', 'ITC.NS', 'LT.NS', 'SBIN.NS', 'BHARTIARTL.NS',
    'ASIANPAINT.NS', 'HINDUNILVR.NS', 'BAJFINANCE.NS', 'AXISBANK.NS', 'HCLTECH.NS',
    'MARUTI.NS', 'SUNPHARMA.NS', 'TITAN.NS', 'WIPRO.NS', 'ULTRACEMCO.NS',
    'NTPC.NS', 'POWERGRID.NS', 'NESTLEIND.NS', 'TECHM.NS', 'BAJAJFINSV.NS',
    'ONGC.NS', 'TATAMOTORS.NS', 'JSWSTEEL.NS', 'COALINDIA.NS', 'HDFCLIFE.NS',
    'GRASIM.NS', 'ADANIENT.NS', 'ADANIPORTS.NS', 'CIPLA.NS', 'DIVISLAB.NS',
    'BAJAJ-AUTO.NS', 'DRREDDY.NS', 'BPCL.NS', 'EICHERMOT.NS', 'SHREECEM.NS',
    'SBILIFE.NS', 'IOC.NS', 'HEROMOTOCO.NS', 'BRITANNIA.NS', 'INDUSINDBK.NS',
    'TATACONSUM.NS', 'PIDILITIND.NS', 'HINDALCO.NS', 'GAIL.NS', 'DABUR.NS',
    'ICICIPRULI.NS', 'HAVELLS.NS', 'AMBUJACEM.NS', 'VEDL.NS', 'UPL.NS',
    'DLF.NS', 'SIEMENS.NS', 'SRF.NS', 'M&M.NS', 'SBICARD.NS',
    'BERGEPAINT.NS', 'BIOCON.NS', 'LUPIN.NS', 'AUROPHARMA.NS', 'TATAPOWER.NS',
    'MUTHOOTFIN.NS', 'BOSCHLTD.NS', 'COLPAL.NS', 'INDIGO.NS', 'MARICO.NS',
    'ICICIGI.NS', 'GODREJCP.NS', 'PEL.NS', 'TORNTPHARM.NS', 'HINDPETRO.NS',
    'BANKBARODA.NS', 'IDFCFIRSTB.NS', 'PNB.NS', 'CANBK.NS', 'UNIONBANK.NS',
    'RECLTD.NS', 'PFC.NS', 'NHPC.NS', 'NMDC.NS', 'SJVN.NS',
    'IRCTC.NS', 'ABB.NS', 'ADANIGREEN.NS', 'ADANITRANS.NS', 'ZOMATO.NS',
    'PAYTM.NS', 'POLYCAB.NS', 'LTTS.NS', 'LTI.NS', 'MINDTREE.NS',
    'MPHASIS.NS', 'COFORGE.NS', 'TATAELXSI.NS', 'NAVINFLUOR.NS', 'ALKEM.NS'
]

# Multiselect
selected_stocks = st.multiselect("Select Stocks to Scan", nifty_100, default=nifty_100[:5])

@st.cache_data
def screen_stocks(stock_list, sma_period, volume_lookback):
    results = []

    for symbol in stock_list:
        try:   #+ ".NS"
            df = yf.download(symbol , period="6mo", interval="1d")
            df.dropna(inplace=True)

            # Calculate SMA manually
            df['sma'] = df['Close'].rolling(window=sma_period).mean()

            # Calculate volume average manually
            df['volume_avg'] = df['Volume'].rolling(window=volume_lookback).mean()

            df = df.dropna()  # Ensure no NaN values in comparison rows

            latest = df.iloc[-1]
            prev = df.iloc[-2]

            if float(latest['Close']) > float(latest['sma']) and float(prev['Close']) < float(prev['sma']):
                if float(latest['Volume']) > float(latest['volume_avg']):
                    results.append({
                        'Symbol': symbol,
                        'Close': round(float(latest['Close']), 2),
                        f'SMA{sma_period}': round(float(latest['sma']), 2),
                        'Volume': int(latest['Volume']),
                        f'VolumeAvg{volume_lookback}': int(latest['volume_avg'])
                    })
        except Exception as e:
            st.warning(f"Error loading {symbol}: {e}")
            continue

    return pd.DataFrame(results)

if st.button("🔍 Run Screener"):
    screener_result = screen_stocks(selected_stocks, sma_period, volume_lookback)
    if not screener_result.empty:
        st.success(f"Found {len(screener_result)} swing candidates")
        st.dataframe(screener_result)
        csv = screener_result.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", csv, "swing_candidates.csv", "text/csv")
    else:
        st.info("No stocks matched the criteria.")
