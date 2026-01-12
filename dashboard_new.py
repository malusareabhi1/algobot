import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(
    page_title="Algo Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
/* Main background */
.stApp {
    background-color: #0E1117;
    color: #FAFAFA;
}

/* Section containers */
.block {
    background-color: #161B22;
    padding: 15px;
    border-radius: 12px;
    box-shadow: 0 0 10px rgba(0,0,0,0.6);
    margin-bottom: 10px;
}

/* Titles */
h1, h2, h3 {
    color: #58A6FF;
}

/* Metric cards */
.metric-green {
    background: linear-gradient(135deg, #0f5132, #198754);
    padding: 12px;
    border-radius: 10px;
    text-align: center;
    font-weight: bold;
}

.metric-red {
    background: linear-gradient(135deg, #842029, #dc3545);
    padding: 12px;
    border-radius: 10px;
    text-align: center;
    font-weight: bold;
}

.metric-blue {
    background: linear-gradient(135deg, #084298, #0d6efd);
    padding: 12px;
    border-radius: 10px;
    text-align: center;
    font-weight: bold;
}

/* DataFrame */
[data-testid="stDataFrame"] {
    background-color: #161B22;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

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
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("Connection Status")

    c1, c2, c3 = st.columns(3)

    c1.markdown('<div class="metric-green">Kite<br>Connected</div>', unsafe_allow_html=True)
    c2.markdown('<div class="metric-blue">WebSocket<br>Running</div>', unsafe_allow_html=True)
    c3.markdown('<div class="metric-green">Funds<br>₹1,02,450</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("NIFTY 5 / 15 Min Chart")

    fig.update_layout(
        template="plotly_dark",
        height=350,
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(fig, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


    st.divider()

    # ===== ROW 2 =====
    col3, col4 = st.columns(2)

with col3:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("Signal Log")
    st.dataframe(signal_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("Option Log")
    st.dataframe(option_df.style.applymap(
        lambda x: "color: #00ff88" if isinstance(x, (int, float)) and x > 0 else
                  "color: #ff4d4d" if isinstance(x, (int, float)) and x < 0 else ""
    ), use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ===== ROW 3 =====
    col5, col6 = st.columns(2)

with col5:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("Parameter Values")

    p1, p2, p3, p4 = st.columns(4)
    p1.markdown('<div class="metric-blue">Strategy<br>Doctor 1.0</div>', unsafe_allow_html=True)
    p2.markdown('<div class="metric-blue">TF<br>5 Min</div>', unsafe_allow_html=True)
    p3.markdown('<div class="metric-red">SL<br>10%</div>', unsafe_allow_html=True)
    p4.markdown('<div class="metric-green">Target<br>15%</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

with col6:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("Greeks Values")

    g1, g2, g3, g4, g5 = st.columns(5)

    g1.metric("Delta", "0.52")
    g2.metric("Gamma", "0.08")
    g3.metric("Theta", "-12.5")
    g4.metric("Vega", "4.2")
    g5.metric("IV %", "18.6")

    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # ===== ROW 4 =====
    col7, col8 = st.columns(2)

with col7:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("Order Book")
    st.dataframe(order_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col8:
    st.markdown('<div class="block">', unsafe_allow_html=True)
    st.subheader("Monitoring Trade / Positions")

    pnl_color = "#00ff88" if pos_df["PnL"].sum() > 0 else "#ff4d4d"

    st.markdown(
        f"<h3 style='color:{pnl_color}'>Total PnL: ₹{pos_df['PnL'].sum()}</h3>",
        unsafe_allow_html=True
    )

    st.dataframe(pos_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)


# -----------------------------
# OTHER MENU PAGES (PLACEHOLDERS)
# -----------------------------
else:
    st.title(menu)
    st.info("Page under construction")
