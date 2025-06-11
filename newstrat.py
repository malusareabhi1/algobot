import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests
from ta.trend import MACD
from ta.momentum import RSIIndicator

# ========================= CONFIG =========================
BOT_TOKEN = "your_telegram_bot_token"
CHAT_ID = "your_chat_id"

# ====================== HELPER FUNCTIONS =====================
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=data)

def fetch_data(symbol, interval='1d', period='3mo'):
    try:
        df = yf.download(symbol, interval=interval, period=period)
        if df.empty or not all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
            st.warning(f"Skipping {symbol} — No valid data.")
            return None
        df.dropna(subset=['Open', 'High', 'Low', 'Close'], inplace=True)
        return df
    except Exception as e:
        st.error(f"{symbol}: Data fetch failed — {e}")
        return None



def apply_strategy(df):
    df = df.copy()
    df.dropna(subset=['Open', 'High', 'Low', 'Close', 'Volume'], inplace=True)

    # Skip processing if not enough candles
    if df['Close'].isnull().sum() > 0 or len(df['Close']) < 50:
        df['buy'] = False
        return df

    # Calculate Indicators
    df['20ema'] = df['Close'].ewm(span=20).mean()
    df['50ema'] = df['Close'].ewm(span=50).mean()
    df['200sma'] = df['Close'].rolling(window=200).mean()
    df['bb_mid'] = df['Close'].rolling(window=20).mean()
    df['bb_std'] = df['Close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
    df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']

    # Safe RSI
    try:
        rsi = RSIIndicator(close=df['Close'].astype(float), window=14)
        df['rsi'] = rsi.rsi()
    except Exception as e:
        df['rsi'] = pd.Series([None] * len(df), index=df.index)

    # Safe MACD
    try:
        macd = MACD(close=df['Close'].astype(float))
        df['macd'] = macd.macd()
        df['signal'] = macd.macd_signal()
    except Exception as e:
        df['macd'] = df['signal'] = pd.Series([None] * len(df), index=df.index)

    # Signal logic
    df['buy'] = (
        (df['Close'] > df['bb_upper']) &
        (df['Close'] > df['20ema']) &
        (df['20ema'] > df['50ema']) &
        (df['50ema'] > df['200sma']) &
        (df['macd'] > df['signal']) &
        (df['rsi'] > 55) & (df['rsi'] < 70)
    )

    df['buy'] = df['buy'].fillna(False)
    return df


def backtest(df):
    capital = 100000
    position = 0
    entry_price = 0
    logs = []

    for i in range(1, len(df)):
        if df['buy'].iloc[i] and position == 0:
            entry_price = df['Close'].iloc[i]
            position = capital // entry_price
            logs.append({'Date': df.index[i], 'Action': 'BUY', 'Price': entry_price})

        elif position > 0:
            current_price = df['Close'].iloc[i]
            if current_price >= entry_price * 1.10 or current_price <= entry_price * 0.95:
                logs.append({'Date': df.index[i], 'Action': 'SELL', 'Price': current_price})
                position = 0

    return pd.DataFrame(logs)

def plot_chart(df, symbol):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['Open'],
                                 high=df['High'],
                                 low=df['Low'],
                                 close=df['Close'],
                                 name='Candles'))
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], line=dict(color='red', width=1), name='BB Upper'))
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], line=dict(color='red', width=1), name='BB Lower'))
    fig.add_trace(go.Scatter(x=df.index, y=df['20ema'], line=dict(color='blue', width=1), name='20 EMA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['50ema'], line=dict(color='orange', width=1), name='50 EMA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['200sma'], line=dict(color='green', width=1), name='200 SMA'))
    fig.update_layout(title=f"{symbol} - Breakout Strategy", xaxis_title="Date", yaxis_title="Price")
    return fig

# ====================== STREAMLIT UI =====================
st.set_page_config("Breakout Strategy - NIFTY 50", layout="wide")
st.title("📈 Breakout Strategy - NIFTY 50")

interval = st.selectbox("Timeframe", ['1d', '15m'])

#nifty_50 = ['RELIANCE.NS', 'INFY.NS', 'TCS.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'LT.NS']  # Add full list
nifty_50 = [
    'RELIANCE.NS', 'HDFCBANK.NS', 'ICICIBANK.NS', 'INFY.NS', 'LT.NS', 'TCS.NS', 'AXISBANK.NS', 'SBIN.NS', 'ITC.NS', 'BHARTIARTL.NS',
    'KOTAKBANK.NS', 'HINDUNILVR.NS', 'BAJFINANCE.NS', 'ASIANPAINT.NS', 'HCLTECH.NS', 'MARUTI.NS', 'SUNPHARMA.NS', 'WIPRO.NS', 'ULTRACEMCO.NS', 'TECHM.NS',
    'POWERGRID.NS', 'TITAN.NS', 'ADANIENT.NS', 'NTPC.NS', 'BAJAJFINSV.NS', 'NESTLEIND.NS', 'TATASTEEL.NS', 'JSWSTEEL.NS', 'GRASIM.NS', 'HDFCLIFE.NS',
    'ONGC.NS', 'ADANIPORTS.NS', 'HINDALCO.NS', 'COALINDIA.NS', 'BPCL.NS', 'EICHERMOT.NS', 'BRITANNIA.NS', 'DIVISLAB.NS', 'CIPLA.NS', 'DRREDDY.NS',
    'HEROMOTOCO.NS', 'BAJAJ_AUTO.NS', 'IOC.NS', 'SBILIFE.NS', 'SHREECEM.NS', 'INDUSINDBK.NS', 'APOLLOHOSP.NS', 'ICICIPRULI.NS', 'PIDILITIND.NS', 'DMART.NS',
    'M&M.NS', 'SIEMENS.NS', 'AMBUJACEM.NS', 'DLF.NS', 'ADANIGREEN.NS', 'BANKBARODA.NS', 'TATAMOTORS.NS', 'INDIGO.NS', 'GODREJCP.NS', 'TRENT.NS',
    'UBL.NS', 'MPHASIS.NS', 'CHOLAFIN.NS', 'SRF.NS', 'TATACONSUM.NS', 'AUROPHARMA.NS', 'ABB.NS', 'BEL.NS', 'IDFCFIRSTB.NS', 'NAUKRI.NS',
    'INDUSTOWER.NS', 'YESBANK.NS', 'BANDHANBNK.NS', 'HAVELLS.NS', 'ALKEM.NS', 'PAGEIND.NS', 'GLAND.NS', 'ZOMATO.NS', 'CANBK.NS', 'VEDL.NS',
    'MARICO.NS', 'LUPIN.NS', 'BOSCHLTD.NS', 'COLPAL.NS', 'TORNTPHARM.NS', 'ICICIGI.NS', 'HDFCAMC.NS', 'MUTHOOTFIN.NS', 'GAIL.NS', 'PETRONET.NS',
    'RECLTD.NS', 'ADANIPOWER.NS', 'MOTHERSON.NS', 'L&TFH.NS', 'GMRINFRA.NS', 'PFC.NS', 'CONCOR.NS', 'TVSMOTOR.NS', 'CUMMINSIND.NS', 'DABUR.NS',
    'IRCTC.NS', 'BERGEPAINT.NS', 'VOLTAS.NS', 'NHPC.NS', 'BIOCON.NS', 'PIIND.NS', 'PNB.NS', 'SYNGENE.NS', 'HINDPETRO.NS', 'ATGL.NS',
    'AARTIIND.NS', 'BALKRISIND.NS', 'SAIL.NS', 'INDIAMART.NS', 'NAVINFLUOR.NS', 'IEX.NS', 'WHIRLPOOL.NS', 'BALRAMCHIN.NS', 'HAL.NS', 'POLYCAB.NS',
    'MFSL.NS', 'TATACHEM.NS', 'ABCAPITAL.NS', 'DEEPAKNTR.NS', 'SUNTV.NS', 'JUBLFOOD.NS', 'RAMCOCEM.NS', 'GODREJPROP.NS', 'ADANITRANS.NS', 'TRIDENT.NS',
    'METROPOLIS.NS', 'GRANULES.NS', 'BATAINDIA.NS', 'RAJESHEXPO.NS', 'IRFC.NS', 'INDHOTEL.NS', 'ESCORTS.NS', 'COROMANDEL.NS', 'SUPREMEIND.NS', 'FORTIS.NS',
    'TATAPOWER.NS', 'LTTS.NS', 'LTI.NS', 'BHEL.NS', 'MRF.NS', 'AUBANK.NS', 'ASHOKLEY.NS', 'VINATIORGA.NS', 'IDBI.NS', 'IGL.NS'
]


for symbol in nifty_50:
    df = fetch_data(symbol, interval=interval)
    
    # Safeguard check
    if df is None or df.empty:
        st.warning(f"Skipping {symbol} — No valid data.")
        continue

    df = apply_strategy(df)

    if df['buy'].iloc[-1]:
        st.subheader(f"✅ Breakout Signal: {symbol}")
        st.plotly_chart(plot_chart(df, symbol), use_container_width=True)
        send_telegram_message(f"📢 Breakout Alert: {symbol} at ₹{df['Close'].iloc[-1]:.2f}")

        if st.button(f"Backtest {symbol}", key=symbol):
            result = backtest(df)
            st.dataframe(result)





