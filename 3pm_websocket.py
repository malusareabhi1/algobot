import os
import threading
from datetime import datetime, timedelta
import pytz
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from kiteconnect import KiteTicker

# -----------------------
# 🔧 USER CONFIG
# -----------------------
API_KEY = os.getenv("KITE_API_KEY", "YOUR_API_KEY")
ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "YOUR_ACCESS_TOKEN")
INSTRUMENT_TOKEN = int(os.getenv("INSTRUMENT_TOKEN", "256265"))  # 256265 = NIFTY 50 spot

IST = pytz.timezone("Asia/Kolkata")

# -----------------------
# 🧠 STATE
# -----------------------
if "ticks_df" not in st.session_state:
    st.session_state.ticks_df = pd.DataFrame(columns=["ts", "ltp"])

if "candles_15m" not in st.session_state:
    st.session_state.candles_15m = pd.DataFrame(
        columns=["Datetime", "Open_^NSEI", "High_^NSEI", "Low_^NSEI", "Close_^NSEI"]
    )

if "lock" not in st.session_state:
    st.session_state.lock = threading.Lock()

if "ws_started" not in st.session_state:
    st.session_state.ws_started = False

# -----------------------
# 🔩 HELPER: Aggregate ticks -> 15m candles
# -----------------------
def update_candles_from_ticks():
    """Aggregate latest ticks into 15-min OHLC candles (IST)."""
    with st.session_state.lock:
        df = st.session_state.ticks_df.copy()
    if df.empty:
        return

    df["ts"] = pd.to_datetime(df["ts"]).dt.tz_convert(IST)
    # Floor to 15-min bins
    df["bin"] = df["ts"].dt.floor("15T")

    agg = df.groupby("bin").agg(
        Open=("ltp", "first"),
        High=("ltp", "max"),
        Low=("ltp", "min"),
        Close=("ltp", "last"),
    ).reset_index().rename(columns={"bin": "Datetime"})

    agg.rename(
        columns={
            "Open": "Open_^NSEI",
            "High": "High_^NSEI",
            "Low": "Low_^NSEI",
            "Close": "Close_^NSEI",
        },
        inplace=True,
    )

    # Keep only market hours 9:15–15:30 IST and trading days
    agg = agg[
        (agg["Datetime"].dt.hour >= 9) & (agg["Datetime"].dt.hour <= 15)
    ]
    # Filter early minutes before 9:15 and after 15:30
    agg = agg[
        ~(
            (agg["Datetime"].dt.hour == 9) & (agg["Datetime"].dt.minute < 15)
        )
        &
        ~(
            (agg["Datetime"].dt.hour == 15) & (agg["Datetime"].dt.minute > 30)
        )
    ]

    with st.session_state.lock:
        # merge incremental
        base = st.session_state.candles_15m
        merged = pd.concat([base, agg], ignore_index=True)
        merged = merged.drop_duplicates(subset=["Datetime"]).sort_values("Datetime")
        st.session_state.candles_15m = merged.reset_index(drop=True)

# -----------------------
# 🔌 WebSocket callbacks
# -----------------------
def start_ws():
    kws = KiteTicker(API_KEY, ACCESS_TOKEN)

    def on_connect(ws, response):
        ws.subscribe([INSTRUMENT_TOKEN])
        ws.set_mode(ws.MODE_FULL, [INSTRUMENT_TOKEN])

    def on_ticks(ws, ticks):
        # Collect ticks into session state
        if not ticks:
            return
        rows = []
        for t in ticks:
            ts = t.get("timestamp")
            ltp = t.get("last_price")
            if ts is None or ltp is None:
                continue
            # NSE feed timestamps are timezone-aware (UTC). Ensure tz-aware:
            if ts.tzinfo is None:
                ts = IST.localize(ts)  # fallback
            rows.append({"ts": ts, "ltp": float(ltp)})

        if rows:
            new_df = pd.DataFrame(rows)
            with st.session_state.lock:
                st.session_state.ticks_df = pd.concat(
                    [st.session_state.ticks_df, new_df], ignore_index=True
                ).tail(20000)  # keep memory bounded

        # After ticks arrive, try update candles
        update_candles_from_ticks()

    def on_error(ws, code, reason):
        # Streamlit-safe light logging
        print("WS error:", code, reason)

    def on_close(ws, code, reason):
        print("WS closed:", code, reason)

    kws.on_connect = on_connect
    kws.on_ticks = on_ticks
    kws.on_error = on_error
    kws.on_close = on_close

    # threaded=True keeps Streamlit responsive
    kws.connect(threaded=True)

# -----------------------
# 📈 Your existing helpers (stubs/placeholders where needed)
# -----------------------
def display_todays_candles_with_trend_and_signal(df):
    if df.empty:
        st.warning("No candle data yet.")
        return
    today_date = df["Datetime"].dt.date.max()
    todays_df = df[df["Datetime"].dt.date == today_date].copy()
    if todays_df.empty:
        st.warning("No candles for today yet.")
        return

    def trend(row):
        if row["Close_^NSEI"] > row["Open_^NSEI"]:
            return "Bullish 🔥"
        elif row["Close_^NSEI"] < row["Open_^NSEI"]:
            return "Bearish ❄️"
        return "Doji ⚪"

    todays_df["Trend"] = todays_df.apply(trend, axis=1)

    sig = []
    for i in range(len(todays_df)):
        if i == 0:
            sig.append("-")
        else:
            prev_high = todays_df.iloc[i-1]["High_^NSEI"]
            prev_low  = todays_df.iloc[i-1]["Low_^NSEI"]
            curr_close = todays_df.iloc[i]["Close_^NSEI"]
            curr_trend = todays_df.iloc[i]["Trend"]
            if curr_trend.startswith("Bullish") and curr_close > prev_high:
                sig.append("Buy")
            elif curr_trend.startswith("Bearish") and curr_close < prev_low:
                sig.append("Sell")
            else:
                sig.append("-")
    todays_df["Signal"] = sig
    todays_df["Time"] = todays_df["Datetime"].dt.strftime("%H:%M")
    display_df = todays_df[["Time","Open_^NSEI","High_^NSEI","Low_^NSEI","Close_^NSEI","Trend","Signal"]].copy()
    display_df.rename(columns={"Open_^NSEI":"Open","High_^NSEI":"High","Low_^NSEI":"Low","Close_^NSEI":"Close"}, inplace=True)
    st.subheader(f"Today's 15-min candles ({today_date})")
    st.table(display_df.tail(10))

def get_nearest_weekly_expiry(today_pd_ts):
    # Simple placeholder: next Thursday in IST
    d = today_pd_ts.date()
    while d.weekday() != 3:  # 0 Mon ... 3 Thu
        d += timedelta(days=1)
    return pd.Timestamp(d)

def trading_signal_all_conditions(df, quantity=10*750):
    # (Same as your implementation; shortened for space)
    if df.empty or len(df) < 2:
        return None
    spot_price = float(df["Close_^NSEI"].iloc[-1])
    df = df.copy()
    df["Date"] = df["Datetime"].dt.date
    unique_days = sorted(df["Date"].unique())
    if len(unique_days) < 2:
        return None
    day0, day1 = unique_days[-2], unique_days[-1]
    c3 = df[(df["Date"]==day0)&(df["Datetime"].dt.hour==15)&(df["Datetime"].dt.minute==0)]
    if c3.empty: return None
    open_3pm = c3.iloc[0]["Open_^NSEI"]; close_3pm = c3.iloc[0]["Close_^NSEI"]
    c930 = df[(df["Date"]==day1)&(df["Datetime"].dt.hour==9)&(df["Datetime"].dt.minute==30-15)]  # 9:15 close at 9:30
    if c930.empty: return None
    open_930 = c930.iloc[0]["Open_^NSEI"]; close_930 = c930.iloc[0]["Close_^NSEI"]
    high_930 = c930.iloc[0]["High_^NSEI"]; low_930 = c930.iloc[0]["Low_^NSEI"]
    entry_time = c930.iloc[0]["Datetime"]

    expiry = get_nearest_weekly_expiry(pd.to_datetime(day1))
    buy_price = close_930; stoploss = buy_price*0.9; take_profit = buy_price*1.1

    # Cond 1
    if (low_930<open_3pm and close_930>open_3pm) and (low_930<close_3pm and close_930>close_3pm):
        return {"condition":1,"option_type":"CALL","buy_price":buy_price,"stoploss":stoploss,"take_profit":take_profit,
                "quantity":quantity,"expiry":expiry,"entry_time":entry_time,"message":"Condition 1: Buy CALL","spot_price":spot_price}
    # Cond 4 (mirror)
    if (high_930>open_3pm and close_930<open_3pm) and (high_930>close_3pm and close_930<close_3pm):
        return {"condition":4,"option_type":"PUT","buy_price":buy_price,"stoploss":stoploss,"take_profit":take_profit,
                "quantity":quantity,"expiry":expiry,"entry_time":entry_time,"message":"Condition 4: Buy PUT","spot_price":spot_price}
    return None

# ---- Stubs you already have in your code ----
def find_nearest_itm_option():
    # Replace with your existing NSE option-chain fetch (DataFrame with strikePrice, expiryDate, optionType, lastPrice, ...)
    # Here we just return empty to avoid runtime errors in the template.
    return pd.DataFrame(columns=["strikePrice","expiryDate","optionType","lastPrice"])

def option_chain_finder(option_chain_df, spot_price, option_type, lots=10, lot_size=75):
    # Put your working implementation here; placeholder:
    return {"strikePrice": None, "expiryDate": None, "optionType": option_type, "total_quantity": lots*lot_size,
            "option_data": {"strikePrice": None, "lastPrice": None, "optionType": option_type, "expiryDate": None}}

def generate_trade_log_from_option(result, signal):
    # Put your working implementation here; minimal safe output:
    if not result or not signal: return pd.DataFrame()
    entry = signal["entry_time"].strftime("%Y-%m-%d %H:%M:%S") if hasattr(signal["entry_time"], "strftime") else str(signal["entry_time"])
    return pd.DataFrame([{
        "Condition": signal.get("condition"),
        "Option Type": signal.get("option_type"),
        "Strike Price": result.get("strikePrice"),
        "Buy Premium": (result.get("option_data") or {}).get("lastPrice"),
        "Quantity": result.get("total_quantity"),
        "Expiry Date": str(result.get("expiryDate")),
        "Entry Time": entry,
        "Trade Message": signal.get("message")
    }])

# -----------------------
# 🚀 UI & Live loop
# -----------------------
st.set_page_config(layout="wide")
st.title("NIFTY — Live 15-min Candles (WebSocket, no refresh)")

col1, col2 = st.columns([2,1])

# Start WS once
if not st.session_state.ws_started:
    st.session_state.ws_started = True
    threading.Thread(target=start_ws, daemon=True).start()
    st.success("WebSocket started ✔️ (KiteTicker)")

# Update candles from whatever ticks we have so far
update_candles_from_ticks()

with col1:
    df = st.session_state.candles_15m.copy()
    if not df.empty:
        fig = go.Figure(data=[go.Candlestick(
            x=df["Datetime"],
            open=df["Open_^NSEI"],
            high=df["High_^NSEI"],
            low=df["Low_^NSEI"],
            close=df["Close_^NSEI"],
        )])
        fig.update_layout(title="NIFTY 15-min Candles (Live)", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Waiting for live ticks to build the first 15-min candle...")

    display_todays_candles_with_trend_and_signal(df)

with col2:
    st.subheader("Signal & Trade")
    if not df.empty:
        signal = trading_signal_all_conditions(df)
        if signal:
            st.success(f"Trade signal: {signal['message']}")
            st.write(signal)

            # Find nearest ITM option as per your logic
            try:
                oc_df = find_nearest_itm_option()
                ot = "CE" if signal["option_type"].upper()=="CALL" else "PE"
                result = option_chain_finder(oc_df, signal["spot_price"], option_type=ot, lots=10, lot_size=75)
                st.write("Nearest ITM option (preview):")
                st.write(result.get("option_data"))

                trade_log_df = generate_trade_log_from_option(result, signal)
                st.write("Trade Log")
                st.table(trade_log_df)
            except Exception as e:
                st.error(f"Option lookup failed: {e}")
        else:
            st.warning("No trade signal yet for current session.")
    else:
        st.info("Signals will appear after first few candles.")

st.caption("Note: WebSocket aggregates ticks into 15-min candles in IST. Keep the app running for continuous updates.")
