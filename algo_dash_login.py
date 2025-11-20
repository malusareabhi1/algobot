import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta

###############################################
# INITIAL SESSION STATE
###############################################
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "open_trade" not in st.session_state:
    st.session_state.open_trade = None

if "orderbook" not in st.session_state:
    st.session_state.orderbook = []


###############################################
# LOGIN SYSTEM
###############################################
def login_ui():
    st.title("Algo Trading Dashboard — Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == "admin" and pwd == "1234":
            st.session_state.logged_in = True
            st.success("Login successful!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Invalid credentials")


###############################################
# PAPER TRADE FUNCTIONS
###############################################
def place_paper_trade(symbol, direction, entry_price, sl, target):
    trade = {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "sl": sl,
        "target": target,
        "qty": 50,
        "entry_time": datetime.now(),
        "status": "OPEN",
    }

    st.session_state.open_trade = trade
    st.session_state.orderbook.append({
        **trade,
        "exit_price": None,
        "exit_time": None,
        "exit_reason": None,
        "pnl": None,
    })

    return trade


def exit_trade(exit_price, reason):
    trade = st.session_state.open_trade
    if trade is None:
        return

    last = st.session_state.orderbook[-1]
    last["exit_price"] = exit_price
    last["exit_time"] = datetime.now()
    last["exit_reason"] = reason

    qty = trade["qty"]

    if trade["direction"] == "CALL":
        pnl = (exit_price - trade["entry_price"]) * qty
    else:
        pnl = (trade["entry_price"] - exit_price) * qty

    last["pnl"] = pnl

    st.session_state.open_trade = None


def monitor_trade(ltp, base_high, base_low):
    trade = st.session_state.open_trade
    if trade is None:
        return None

    direction = trade["direction"]
    entry_time = trade["entry_time"]
    elapsed_min = (datetime.now() - entry_time).seconds / 60

    # STOPLOSS
    if direction == "CALL" and ltp <= trade["sl"]:
        exit_trade(ltp, "SL HIT")
        return

    if direction == "PUT" and ltp >= trade["sl"]:
        exit_trade(ltp, "SL HIT")
        return

    # TARGET
    if direction == "CALL" and ltp >= trade["target"]:
        exit_trade(ltp, "TARGET HIT")
        return

    if direction == "PUT" and ltp <= trade["target"]:
        exit_trade(ltp, "TARGET HIT")
        return

    # TIME EXIT (16 minutes)
    if elapsed_min >= 16:
        exit_trade(ltp, "TIME EXIT")
        return

    # FLIP LOGIC
    if direction == "CALL" and ltp < base_low:
        exit_trade(ltp, "FLIP: CALL EXIT → MAKE PUT")
        return "FLIP_PUT"

    if direction == "PUT" and ltp > base_high:
        exit_trade(ltp, "FLIP: PUT EXIT → MAKE CALL")
        return "FLIP_CALL"


###############################################
# STRATEGY ENGINE
###############################################
def apply_strategy(base_high, base_low, H1, L1, C1):
    # Condition 1: Bullish Breakout
    if L1 >= base_high and H1 >= base_low and C1 >= base_high:
        sl = L1
        target = H1 * 1.10
        place_paper_trade("NIFTY_CALL", "CALL", H1, sl, target)
        return "CALL ENTRY"

    # Condition 2: Bearish Breakdown
    elif L1 <= base_high and H1 <= base_low and C1 <= base_low:
        sl = H1
        target = L1 * 0.90
        place_paper_trade("NIFTY_PUT", "PUT", L1, sl, target)
        return "PUT ENTRY"

    # Condition 3: Gap Up
    elif C1 > base_high:
        place_paper_trade("NIFTY_CALL", "CALL", H1, H1 - 15, H1 * 1.10)
        return "GAP UP CALL"

    # Condition 4: Gap Down
    elif C1 < base_low:
        place_paper_trade("NIFTY_PUT", "PUT", L1, L1 + 15, L1 * 0.90)
        return "GAP DOWN PUT"

    return "NO TRADE"


###############################################
# DASHBOARD UI
###############################################
def dashboard():
    st.title("Algo Trading Dashboard — Base Zone Strategy")

    st.subheader("Base Zone Inputs")
    base_high = st.number_input("Previous Day 3PM Candle OPEN (Base High)")
    base_low = st.number_input("Previous Day 3PM Candle CLOSE (Base Low)")

    st.subheader("Today's First 15-min Candle")
    H1 = st.number_input("H1 — High")
    L1 = st.number_input("L1 — Low")
    C1 = st.number_input("C1 — Close")

    if st.button("Run Strategy & Generate Entry"):
        signal = apply_strategy(base_high, base_low, H1, L1, C1)
        st.success(f"Signal: {signal}")

    st.subheader("Live LTP Simulation")
    ltp = st.number_input("Live Price (LTP)")

    if st.button("Monitor Trade"):
        result = monitor_trade(ltp, base_high, base_low)
        if result == "FLIP_CALL":
            place_paper_trade("NIFTY_CALL", "CALL", ltp, ltp-15, ltp*1.10)
        elif result == "FLIP_PUT":
            place_paper_trade("NIFTY_PUT", "PUT", ltp, ltp+15, ltp*0.90)

    st.subheader("Open Trade")
    st.write(st.session_state.open_trade)

    st.subheader("Orderbook")
    if st.session_state.orderbook:
        df = pd.DataFrame(st.session_state.orderbook)
        st.dataframe(df, use_container_width=True)


###############################################
# MAIN APP
###############################################
if not st.session_state.logged_in:
    login_ui()
else:
    dashboard()
