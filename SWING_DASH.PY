import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("📈 NIFTY200 — Strong Uptrend + High Volume Scanner")

# -------- NIFTY 200 STOCK LIST ----------
nifty200 = [
    "ABB.NS","ACC.NS","AIAENG.NS","APLAPOLLO.NS","AUBANK.NS","ABBOTINDIA.NS","ADANIPORTS.NS",
    "ASIANPAINT.NS","ATGL.NS","AXISBANK.NS","BAJAJFINSV.NS","BAJFINANCE.NS","BAJAJHLDNG.NS",
    "BERGEPAINT.NS","BHARTIARTL.NS","BHEL.NS",
    # 📌 Add full list here if needed
]

# -----------------------------------------
st.subheader("Scanning stocks… Please wait ⏳")
uptrend = []

for symbol in nifty200:
    try:
        df = yf.download(symbol, period="8mo", interval="1d", progress=False)
        if len(df) < 200:
            continue

        # Indicators
        df["EMA50"] = df["Close"].ewm(span=50).mean()
        df["EMA200"] = df["Close"].ewm(span=200).mean()
        df["RSI"] = df["Close"].diff().apply(lambda x: x if x > 0 else 0).rolling(14).mean() / \
                    abs(df["Close"].diff()).rolling(14).mean() * 100

        df["MACD"] = df["Close"].ewm(12).mean() - df["Close"].ewm(26).mean()
        df["Signal"] = df["MACD"].ewm(9).mean()
        df["Hist"] = df["MACD"] - df["Signal"]

        df["Vol20"] = df["Volume"].rolling(20).mean()

        latest = df.iloc[-1]

        # ---------- STRONG TREND CONDITIONS ----------
        cond1 = latest["Close"] > latest["EMA50"]
        cond2 = latest["EMA50"] > latest["EMA200"]
        cond3 = latest["Hist"] > 0
        cond4 = latest["RSI"] > 55
        cond5 = latest["Volume"] > latest["Vol20"]   # High volume trend

        if cond1 and cond2 and cond3 and cond4 and cond5:
            uptrend.append(symbol.replace(".NS", ""))

    except:
        pass

# -----------------------------------------
st.subheader("🔥 Strong Uptrend + High Volume Stocks")
df_list = pd.DataFrame(uptrend, columns=["Trending Stocks"])

if len(uptrend) > 0:
    st.dataframe(df_list, use_container_width=True)

    selected = st.selectbox("📊 Select stock to view chart", uptrend)

    if selected:
        symbol = selected + ".NS"
        df = yf.download(symbol, period="8mo", interval="1d", progress=False)

        df["EMA50"] = df["Close"].ewm(span=50).mean()
        df["EMA200"] = df["Close"].ewm(span=200).mean()

        # ----------- PLOTLY CHART -----------
        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candles"
        ))

        fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"], line=dict(width=1.5), name="EMA50"))
        fig.add_trace(go.Scatter(x=df.index, y=df["EMA200"], line=dict(width=1.5), name="EMA200"))

        fig.update_layout(
            title=f"{selected} — Trend Chart",
            height=600,
            xaxis_rangeslider_visible=False
        )

        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No stocks currently match all strong uptrend conditions.")
