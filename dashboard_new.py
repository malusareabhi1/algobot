import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Algo Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# SIDEBAR MENU
# -----------------------------
st.sidebar.title("MENU")

menu = st.sidebar.radio(
    "",
    [
        "Home",
        "Strategies",
        "Dashboard",
        "API",
        "Live Trade",
        "Settings",
        "Logout"
    ]
)

# -----------------------------
# DASHBOARD PAGE
# -----------------------------
if menu == "Dashboard":

    st.title("Algo Trading Dashboard")

    # ===== ROW 1 =====
    col1, col2 = st.columns([1, 3])

    with col1:
        st.subheader("Connection Status")
        st.success("Kite Connected")
        st.info("WebSocket: Running")
        st.metric("Funds", "₹1,02,450")

    with col2:
        st.subheader("NIFTY 5 / 15 Min Chart")

        # Placeholder chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[1, 2, 3, 4, 5],
            y=[25000, 25100, 25050, 25200, 25180],
            mode="lines",
            name="NIFTY"
        ))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ===== ROW 2 =====
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Signal Log")
        signal_df = pd.DataFrame({
            "Time": ["09:35", "09:50"],
            "Signal": ["BUY CALL", "BUY PUT"],
            "Strike": [25200, 25100],
            "Status": ["Triggered", "Waiting"]
        })
        st.dataframe(signal_df, use_container_width=True)

    with col4:
        st.subheader("Option Log")
        option_df = pd.DataFrame({
            "Symbol": ["NIFTY25200CE", "NIFTY25100PE"],
            "Entry": [120.5, 98.2],
            "LTP": [135.0, 92.0],
            "PnL": [1450, -390]
        })
        st.dataframe(option_df, use_container_width=True)

    st.divider()

    # ===== ROW 3 =====
    col5, col6 = st.columns(2)

    with col5:
        st.subheader("Parameter Values")
        st.write({
            "Strategy": "Doctor Strategy 1.0",
            "Timeframe": "5 Min",
            "SL %": "10%",
            "Target %": "15%",
            "Trailing SL": "Enabled"
        })

    with col6:
        st.subheader("Greeks Values")
        greeks_df = pd.DataFrame({
            "Greek": ["Delta", "Gamma", "Theta", "Vega", "IV"],
            "Value": [0.52, 0.08, -12.5, 4.2, 18.6]
        })
        st.dataframe(greeks_df, use_container_width=True)

    st.divider()

    # ===== ROW 4 =====
    col7, col8 = st.columns(2)

    with col7:
        st.subheader("Order Book")
        order_df = pd.DataFrame({
            "Order ID": [101, 102],
            "Type": ["BUY", "SELL"],
            "Qty": [50, 50],
            "Price": [120.5, 135.0],
            "Status": ["COMPLETE", "OPEN"]
        })
        st.dataframe(order_df, use_container_width=True)

    with col8:
        st.subheader("Monitoring Trade / Positions")
        pos_df = pd.DataFrame({
            "Symbol": ["NIFTY25200CE"],
            "Qty": [50],
            "Entry": [120.5],
            "LTP": [135.0],
            "PnL": [1450]
        })
        st.dataframe(pos_df, use_container_width=True)

# -----------------------------
# OTHER MENU PAGES (PLACEHOLDERS)
# -----------------------------
else:
    st.title(menu)
    st.info("Page under construction")
