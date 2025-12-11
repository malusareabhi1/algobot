# app_live_nifty_15m.py

import streamlit as st
from streamlit_autorefresh import st_autorefresh

import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

from datetime import datetime, time
import pytz

# ------------------ CONFIG ------------------ #
st.set_page_config(
    page_title="Live NIFTY 15m Trade",
    layout="wide"
)

IST = pytz.timezone("Asia/Kolkata")
MARKET_START = time(9, 30)
MARKET_END = time(15, 25)

REFRESH_MS = 60_000  # 1 minute


# ------------------ DATA LAYER ------------------ #
@st.cache_data(ttl=30)
def get_nifty_15m_latest():
    """
    Fetch last 2 days of 15-minute candles for NIFTY 50 (^NSEI).
    Uses `period` for intraday reliability instead of start/end. [web:20]
    """
    df = yf.download(
        "^NSEI",
        period="2d",
        interval="15m",
        auto_adjust=False,
        progress=False
    )
    if df.empty:
        return df

    df.reset_index(inplace=True)

    # yfinance usually gives 'Datetime' for intraday; normalize if needed. [web:26]
    if 'Datetime' not in df.columns and 'datetime' in df.columns:
        df.rename(columns={'datetime': 'Datetime'}, inplace=True)

    # Make timezone-aware and convert to IST
    if df['Datetime'].dt.tz is None:
        df['Datetime'] = df['Datetime'].dt.tz_localize('UTC').dt.tz_convert(IST)
    else:
        df['Datetime'] = df['Datetime'].dt.tz_convert(IST)

    return df


# ------------------ SIGNAL ENGINE (PLACEHOLDER) ------------------ #
def check_signal(df: pd.DataFrame):
    """
    Example signal function.
    Replace with your real logic (price action, indicators, etc.).
    Receives full 15m dataframe, returns e.g. 'BUY', 'SELL', or None.
    """
    if df.empty:
        return None

    # toy example: BUY when last close > previous close by 0.5%
    if len(df) < 2:
        return None

    last_close = df["Close"].iloc[-1]
    prev_close = df["Close"].iloc[-2]

    if last_close > prev_close * 1.005:
        return "BUY"
    elif last_close < prev_close * 0.995:
        return "SELL"
    else:
        return None


# ------------------ UTILITIES ------------------ #
def is_market_open(now_ist: datetime) -> bool:
    t = now_ist.time()
    return MARKET_START <= t <= MARKET_END


def plot_nifty_15m(df: pd.DataFrame):
    """
    Plot last 2 trading days of 15m candles with Plotly. [web:31]
    """
    if df.empty:
        st.warning("No data available to plot.")
        return

    unique_days = df["Datetime"].dt.date.unique()
    if len(unique_days) >= 2:
        last_day = unique_days[-2]
        today = unique_days[-1]
        df_plot = df[df["Datetime"].dt.date.isin([last_day, today])]
    else:
        df_plot = df

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df_plot["Datetime"],
                open=df_plot["Open"],
                high=df_plot["High"],
                low=df_plot["Low"],
                close=df_plot["Close"],
                name="NIFTY 15m"
            )
        ]
    )

    fig.update_layout(
        title="NIFTY 50 - 15 Minute Live Candles (Last 2 Sessions)",
        xaxis_rangeslider_visible=False,
        xaxis=dict(
            rangebreaks=[
                dict(bounds=["sat", "mon"]),          # hide weekends
                dict(bounds=[15.5, 9.25], pattern="hour"),  # hide off‑market hours
            ]
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


# ------------------ MAIN APP ------------------ #
def main():
    st.title("🔴 LIVE TRADE 3 – NIFTY 50 (15m)")

    # Initialize session state
    if "last_candle_time" not in st.session_state:
        st.session_state.last_candle_time = None
    if "last_signal" not in st.session_state:
        st.session_state.last_signal = None

    # Auto‑refresh only in market hours. [web:15][web:24]
    now_ist = datetime.now(IST)
    if is_market_open(now_ist):
        st_autorefresh(interval=REFRESH_MS, key="refresh_live3")
        st.caption(f"Auto‑refresh ON (every {REFRESH_MS // 1000} sec) – Market hours.")
    else:
        st.caption("Auto‑refresh OFF – outside market hours (9:30–15:25 IST).")

    # Fetch data
    df = get_nifty_15m_latest()
    if df.empty:
        st.error("No intraday NIFTY data available.")
        return

    # Latest completed candle
    last_candle = df.iloc[-1]
    last_time = last_candle["Datetime"]

    st.subheader("Latest 15‑minute candle")
    st.write(
        f"Time (IST): {last_time} | Open: {last_candle['Open']:.2f} | "
        f"High: {last_candle['High']:.2f} | Low: {last_candle['Low']:.2f} | "
        f"Close: {last_candle['Close']:.2f}"
    )

    # New candle detection using session_state. [web:27][web:37]
    new_candle = (
        st.session_state.last_candle_time is None
        or last_time > st.session_state.last_candle_time
    )

    if new_candle:
        # Run your signal engine once per new candle
        signal = check_signal(df)
        st.session_state.last_candle_time = last_time
        st.session_state.last_signal = signal

        if signal is not None:
            st.success(f"New signal on {last_time}: {signal}")
            # TODO: plug in your order execution logic here
            # example: place_order(signal, last_candle)
        else:
            st.info("No signal on latest completed candle.")
    else:
        if st.session_state.last_signal is not None:
            st.info(f"No new candle yet. Last signal: {st.session_state.last_signal}")
        else:
            st.info("No new candle yet and no prior signal.")

    # Plot chart
    st.markdown("---")
    plot_nifty_15m(df)


if __name__ == "__main__":
    main()
