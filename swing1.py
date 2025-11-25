import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import datetime as dt
from functools import lru_cache
import io

# ---------- Helper indicators ----------

def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(com=period - 1, adjust=False).mean()
    ma_down = down.ewm(com=period - 1, adjust=False).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))


def atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.rolling(period).mean()


# Simple SuperTrend implementation
def supertrend(df, period=10, multiplier=3):
    hl2 = (df['High'] + df['Low']) / 2
    atrv = atr(df, period)
    upperband = hl2 + (multiplier * atrv)
    lowerband = hl2 - (multiplier * atrv)
    final_upper = upperband.copy()
    final_lower = lowerband.copy()
    for i in range(1, len(df)):
        if (upperband.iloc[i] < final_upper.iloc[i-1]) or (df['Close'].iloc[i-1] > final_upper.iloc[i-1]):
            final_upper.iloc[i] = upperband.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]
        if (lowerband.iloc[i] > final_lower.iloc[i-1]) or (df['Close'].iloc[i-1] < final_lower.iloc[i-1]):
            final_lower.iloc[i] = lowerband.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]
    supertrend = pd.Series(index=df.index)
    in_uptrend = True
    for i in range(len(df)):
        if df['Close'].iloc[i] <= final_upper.iloc[i]:
            in_uptrend = False
            supertrend.iloc[i] = final_upper.iloc[i]
        else:
            in_uptrend = True
            supertrend.iloc[i] = final_lower.iloc[i]
    return supertrend


# ---------- Strategy implementations (heuristic/simplified) ----------

def strategy_ema44_breakout(df):
    # 44 EMA rising and breakout candle
    df = df.copy()
    df['EMA44'] = ema(df['Close'], 44)
    df['EMA44_slope'] = df['EMA44'].diff(5)
    df['PrevHigh'] = df['High'].shift(1)
    cond = (
        (df['Close'].iloc[-1] > df['EMA44'].iloc[-1]) and
        (df['EMA44_slope'].iloc[-1] > 0) and
        (df['Close'].iloc[-1] > df['PrevHigh'].iloc[-1])
    )
    return cond


def strategy_rsi_squeeze_breakout(df):
    # RSI 40-60 squeeze then breakout above recent 10-day high
    df = df.copy()
    df['RSI'] = rsi(df['Close'], 14)
    last_rsi = df['RSI'].iloc[-6:-1]
    cond_rsi = last_rsi.between(40, 60).all()
    recent_high = df['High'].rolling(10).max().iloc[-2]
    cond_break = df['Close'].iloc[-1] > recent_high
    return cond_rsi and cond_break


def strategy_supertrend_ema_pullback(df):
    # Price >200 EMA, supertrend buy, pullback to 20 EMA with bullish rejection
    df = df.copy()
    df['EMA200'] = ema(df['Close'], 200)
    df['EMA20'] = ema(df['Close'], 20)
    if len(df) < 220:
        return False
    st = supertrend(df, period=10, multiplier=3)
    # supertrend lower value close to price means uptrend
    cond = (
        (df['Close'].iloc[-1] > df['EMA200'].iloc[-1]) and
        (df['Close'].iloc[-1] > st.iloc[-1]) and
        (df['Low'].iloc[-1] <= df['EMA20'].iloc[-1] * 1.02) and
        (df['Close'].iloc[-1] > df['Open'].iloc[-1])
    )
    return cond


def strategy_cup_handle(df):
    # Simplified: check for cup depth and recent breakout above 60-day high
    df = df.copy()
    window = 60
    if len(df) < window + 5:
        return False
    recent = df[-(window+5):]
    left_max = recent['Close'][:int(len(recent)/2)].max()
    right_max = recent['Close'][int(len(recent)/2):].max()
    cup_depth = (max(left_max, right_max) - recent['Close'].min()) / max(left_max, right_max)
    breakout_level = recent['Close'][:window].max()
    cond = (cup_depth > 0.12) and (df['Close'].iloc[-1] > breakout_level)
    return cond


def strategy_vcp(df):
    # Simplified VCP: decreasing volatility over 60 days and breakout
    df = df.copy()
    if len(df) < 90:
        return False
    vol1 = df['Close'].pct_change().rolling(10).std().iloc[-40:-30].mean()
    vol2 = df['Close'].pct_change().rolling(10).std().iloc[-20:-10].mean()
    cond_vol = vol2 < vol1 * 0.9
    pivot = df['High'].rolling(25).max().iloc[-2]
    cond_break = df['Close'].iloc[-1] > pivot
    return cond_vol and cond_break


# ---------- Data fetching & utility ----------
@st.cache_data(ttl=3600)
def fetch_ohlc(ticker, period='1y', interval='1d'):
    try:
        data = yf.download(ticker, period=period, interval=interval, progress=False, threads=False)
        if data.empty:
            return None
        data.dropna(inplace=True)
        return data
    except Exception as e:
        return None


def add_ns(ticker):
    # Add .NS suffix if not present
    return ticker if ticker.upper().endswith('.NS') else ticker + '.NS'


# ---------- Streamlit UI ----------
st.set_page_config(page_title='NIFTY500 Swing Scanner', layout='wide')
st.title('NIFTY500 — Multi-Strategy Swing Scanner')
st.markdown("""
This dashboard scans a list of NIFTY500 tickers (you can upload your CSV) using 5 heuristic swing strategies:
1. EMA44 rising + breakout
2. RSI 40-60 squeeze + breakout
3. SuperTrend + EMA pullback
4. Cup & Handle (simplified)
5. Volatility Contraction Pattern (VCP) simplified

**Note:** These are simplified heuristics for screening. Use backtesting and manual verification before trading.
""")

# Sidebar inputs
st.sidebar.header('Scan Settings')
uploaded = st.sidebar.file_uploader('Upload CSV of tickers (one per line, NSE symbols without .NS ok)', type=['csv', 'txt'])
use_sample = st.sidebar.checkbox('Use sample ticker list (small subset)', value=False)
period = st.sidebar.selectbox('Historical period to fetch', ['6mo', '1y', '2y'], index=1)
interval = st.sidebar.selectbox('Data interval', ['1d'], index=0)
selected_strats = st.sidebar.multiselect('Select strategies to run',
                                        ['EMA44 Breakout','RSI Squeeze Breakout','SuperTrend+EMA Pullback','Cup & Handle','VCP'],
                                        default=['EMA44 Breakout','RSI Squeeze Breakout','SuperTrend+EMA Pullback','Cup & Handle','VCP'])
min_volume = st.sidebar.number_input('Min average volume (last 30 days)', value=0)

# Load tickers
if uploaded is not None:
    try:
        df_in = pd.read_csv(uploaded, header=None)
        tickers = df_in[0].astype(str).str.strip().tolist()
    except Exception:
        content = uploaded.getvalue().decode('utf-8')
        tickers = [line.strip() for line in content.splitlines() if line.strip()]
elif use_sample:
    tickers = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'LT', 'KOTAKBANK', 'SBIN']
else:
    st.sidebar.info('No CSV uploaded — please upload a ticker list or select sample.')
    tickers = []

if not tickers:
    st.warning('No tickers to scan. Upload a CSV or enable sample list in sidebar.')
    st.stop()

# prepare
ns_tickers = [add_ns(t) for t in tickers]

# Scan button
if st.button('Run Scan'):
    results = []
    progress = st.progress(0)
    total = len(ns_tickers)
    for i, t in enumerate(ns_tickers):
        progress.progress(int((i/total)*100))
        df = fetch_ohlc(t, period=period, interval=interval)
        if df is None or df.shape[0] < 60:
            continue
        # optional volume filter
        avg_vol = df['Volume'].tail(30).mean()
        if avg_vol < min_volume:
            continue
        flags = []
        try:
            if 'EMA44 Breakout' in selected_strats and strategy_ema44_breakout(df):
                flags.append('EMA44')
            if 'RSI Squeeze Breakout' in selected_strats and strategy_rsi_squeeze_breakout(df):
                flags.append('RSI-SQZ')
            if 'SuperTrend+EMA Pullback' in selected_strats and strategy_supertrend_ema_pullback(df):
                flags.append('SuperTrend')
            if 'Cup & Handle' in selected_strats and strategy_cup_handle(df):
                flags.append('CupHandle')
            if 'VCP' in selected_strats and strategy_vcp(df):
                flags.append('VCP')
        except Exception as e:
            # skip symbol on any error
            continue
        if flags:
            results.append({'Ticker': t.replace('.NS',''), 'Flags': ','.join(flags), 'AvgVol30': int(avg_vol)})
    progress.progress(100)
    if not results:
        st.info('No matches found for selected strategies.')
    else:
        res_df = pd.DataFrame(results).sort_values(by='AvgVol30', ascending=False)
        st.success(f'Found {len(res_df)} candidates')
        st.dataframe(res_df)
        csv = res_df.to_csv(index=False).encode('utf-8')
        st.download_button('Download CSV', data=csv, file_name='swing_scan_results.csv', mime='text/csv')

        # allow user to select a ticker to view chart
        sel = st.selectbox('Select ticker to view chart', res_df['Ticker'].tolist())
        if sel:
            sel_full = add_ns(sel)
            dfc = fetch_ohlc(sel_full, period='2y')
            st.line_chart(dfc['Close'])

st.markdown('---')
st.caption('This scanner is for educational and screening purposes only. Backtest and verify before placing real trades.')
