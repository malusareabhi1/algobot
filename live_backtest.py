import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
import datetime
import threading

# Initialize session state variables
if 'running' not in st.session_state:
    st.session_state.running = False
if 'index' not in st.session_state:
    st.session_state.index = 20
if 'df' not in st.session_state:
    st.session_state.df = None
if 'signals' not in st.session_state:
    st.session_state.signals = []
if 'pnl' not in st.session_state:
    st.session_state.pnl = 0.0

st.set_page_config(page_title="Live Backtest Simulation", layout="wide")
st.title("📈 Live Backtest Simulation - Streamlit")

# Sidebar
st.sidebar.header("Upload & Controls")
uploaded_file = st.sidebar.file_uploader("Upload CSV File", type=['csv'])
start_button = st.sidebar.button("▶ Start")
pause_button = st.sidebar.button("⏸ Pause")

# Load CSV
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df['DateTime'] = pd.to_datetime(df['DateTime'])
    st.session_state.df = df

# Start or Pause
if start_button:
    st.session_state.running = True
if pause_button:
    st.session_state.running = False

# Strategy logic

def check_strategy(df):
    if df['Close'].iloc[-1] > df['Close'].rolling(20).mean().iloc[-1]:
        return "BUY"
    return "HOLD"

# Live update function
placeholder = st.empty()
chart_area = st.empty()

if st.session_state.df is not None:
    df = st.session_state.df

    def run_live():
        while st.session_state.running and st.session_state.index < len(df):
            i = st.session_state.index
            live_df = df.iloc[:i+1]
            signal = check_strategy(live_df)

            if signal == "BUY":
                st.session_state.signals.append((live_df['DateTime'].iloc[-1], signal, live_df['Close'].iloc[-1]))

            # P&L Paper Trade Example
            if len(st.session_state.signals) >= 2:
                entry_price = st.session_state.signals[-2][2]
                exit_price = st.session_state.signals[-1][2]
                st.session_state.pnl += (exit_price - entry_price)

            # Display Info
            with placeholder.container():
                st.subheader(f"Time: {live_df['DateTime'].iloc[-1]}")
                st.metric(label="Current Close", value=f"{live_df['Close'].iloc[-1]:.2f}")
                st.metric(label="Signal", value=signal)
                st.metric(label="Paper Trade P&L", value=f"₹{st.session_state.pnl:.2f}")

            # Plot chart
            fig = go.Figure()
            fig.add_trace(go.Candlestick(
                x=live_df['DateTime'],
                open=live_df['Open'],
                high=live_df['High'],
                low=live_df['Low'],
                close=live_df['Close'],
                name='Candles'
            ))
            fig.update_layout(height=400, xaxis_rangeslider_visible=False)
            chart_area.plotly_chart(fig, use_container_width=True)

            st.session_state.index += 1
            time.sleep(2)

    # Run live simulation in thread
    if st.session_state.running:
        threading.Thread(target=run_live).start()
