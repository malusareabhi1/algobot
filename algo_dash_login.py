import streamlit as st
import hashlib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

#############################################
# PASSWORD UTILS
#############################################
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# USER DATABASE (HASHED PASSWORDS)
USERS = {
    "admin": hash_password("admin"),
    "shree": hash_password("shree"),
}

#############################################
# LOGIN COMPONENT
#############################################
def login_screen():
    st.title("🔐 Algo Trading Dashboard Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if username in USERS and USERS[username] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.success("Login Successful! Redirecting...")
                st.rerun()
            else:
                st.error("Invalid username or password ❌")

#############################################
# SIDEBAR MENU
#############################################
def sidebar_menu():
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown("---")
        return st.radio("📌 Menu", [
            "Dashboard",
            "Market Data",
            "Strategy Signals",
            "Backtest",
            "Order Log",
            "Settings",
        ])

#############################################
# DASHBOARD
#############################################
def dashboard_home():
    st.title("📊 Algo Trading Dashboard")
    col1, col2, col3 = st.columns(3)
    col1.metric("Today's PnL", "₹ 2,450", "+4.2%")
    col2.metric("Total Trades", "12")
    col3.metric("Win Rate", "67%")

    st.markdown("---")
    st.subheader("Market Trend Overview (NIFTY 50)")
    df = get_dummy_chart_data()
    fig = px.line(df, x="time", y="price", title="NIFTY Trend")
    st.plotly_chart(fig, use_container_width=True)

#############################################
# MARKET DATA PAGE
#############################################
def market_data_page():
    st.title("📈 Live Market Data")
    df = get_dummy_chart_data()

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["time"],
        open=df["open"], high=df["high"], low=df["low"], close=df["close"]
    ))
    fig.update_layout(height=500)
    st.plotly_chart(fig, use_container_width=True)

#############################################
# STRATEGY SIGNALS
#############################################
def strategy_signals():
    st.title("⚡ Strategy Signals (Live)")
    st.info("Signals auto-update based on strategy conditions.")

    # Dummy signal
    signal = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "symbol": "NIFTY24NOVFUT",
        "signal": "BUY",
        "price": 22450,
        "strength": "Strong"
    }

    st.success(f"{signal['time']} → {signal['symbol']} → {signal['signal']} at {signal['price']}")

#############################################
# BACKTEST SECTION
#############################################
def backtest_section():
    st.title("📘 Strategy Backtest")
    uploaded = st.file_uploader("Upload OHLC CSV")

    if uploaded:
        df = pd.read_csv(uploaded)
        st.write("Data Preview", df.head())

        df["Returns"] = df["Close"].pct_change()
        st.line_chart(df["Returns"].cumsum())

#############################################
# ORDER LOG
#############################################
def order_log_page():
    st.title("📜 Order Log")
    st.write("Your executed/paper trades will appear here.")
    st.table(pd.DataFrame({
        "Time": ["09:20", "10:15", "11:40"],
        "Symbol": ["NIFTY24NOVFUT", "BANKNIFTY24NOVFUT", "NIFTY24NOVFUT"],
        "Action": ["BUY", "SELL", "SELL"],
        "Qty": [50, 30, 50],
        "Price": [22400, 48920, 22510]
    }))

#############################################
# SETTINGS
#############################################
def settings_page():
    st.title("⚙️ Settings")
    st.write("Update user preferences, API Keys, Alerts, Theme.")

    st.text_input("Zerodha API Key")
    st.text_input("Zerodha API Secret")
    st.text_input("Telegram Bot Token")

    st.button("Save Settings")

#############################################
# UTILS
#############################################
def get_dummy_chart_data():
    times = pd.date_range(datetime.now() - timedelta(hours=1), periods=30, freq="2min")
    price = 22000 + (pd.Series(range(30)) * 5)
    df = pd.DataFrame({
        "time": times,
        "price": price,
        "open": price - 10,
        "high": price + 20,
        "low": price - 30,
        "close": price,
    })
    return df

#############################################
# MAIN APP
#############################################
def main():
    st.set_page_config(page_title="Algo Dashboard", layout="wide")

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        login_screen()
        return

    # Sidebar
    choice = sidebar_menu()
    if st.sidebar.button("Logout"):
        st.session_state.clear()
        st.rerun()

    # Routing
    if choice == "Dashboard":
        dashboard_home()
    elif choice == "Market Data":
        market_data_page()
    elif choice == "Strategy Signals":
        strategy_signals()
    elif choice == "Backtest":
        backtest_section()
    elif choice == "Order Log":
        order_log_page()
    elif choice == "Settings":
        settings_page()

if __name__ == "__main__":
    main()
