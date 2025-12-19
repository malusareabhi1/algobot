import streamlit as st
import pandas as pd
import numpy as np

# ----------------- Strategy functions -----------------

def compute_ma_signals(df, risk_rr=3.0):
    """
    Simple Siddharth-style 44 MA + 200 MA swing strategy on daily data.

    Columns required in df:
        Date / Datetime, Open, High, Low, Close
    """
    df = df.copy()

    # Normalise column names (change here if your CSV is different)
    rename_map = {}
    for col in df.columns:
        lc = col.lower()
        if lc.startswith("date") or lc.startswith("time"):
            rename_map[col] = "Date"
        elif lc.startswith("open"):
            rename_map[col] = "Open"
        elif lc.startswith("high"):
            rename_map[col] = "High"
        elif lc.startswith("low"):
            rename_map[col] = "Low"
        elif lc.startswith("close"):
            rename_map[col] = "Close"
    df = df.rename(columns=rename_map)

    # Ensure datetime
    if "Date" not in df.columns:
        raise ValueError("CSV must contain a Date/Datetime column")
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    # Moving averages
    df["MA44"] = df["Close"].rolling(44).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    # Trend filter: uptrend only (price & 44MA above 200MA, 44MA rising)
    df["trend_up"] = (
        (df["Close"] > df["MA200"]) &
        (df["MA44"] > df["MA200"]) &
        (df["MA44"] > df["MA44"].shift(1))
    )

    signals = []
    in_trade = False
    entry_price = sl = target = None
    entry_date = None

    for i in range(1, len(df)):
        row_prev = df.iloc[i-1]
        row = df.iloc[i]

        # Skip if MA not available yet
        if np.isnan(row["MA44"]) or np.isnan(row["MA200"]):
            continue

        # If in trade, check exit
        if in_trade:
            # SL hit
            if row["Low"] <= sl:
                exit_price = sl
                exit_reason = "SL hit"
                in_trade = False
            # Target hit
            elif row["High"] >= target:
                exit_price = target
                exit_reason = "Target hit"
                in_trade = False
            else:
                # continue holding
                continue

            signals[-1].update({
                "exit_date": row["Date"],
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "pnl": (exit_price - entry_price)
            })
            continue

        # Not in trade: look for long setup
        # 1) Trend must be up
        if not row["trend_up"]:
            continue

        # 2) Previous candle low touches/near 44MA (pullback to MA)
        #    and current candle breaks previous high
        touch_prev = row_prev["Low"] <= row_prev["MA44"] <= row_prev["High"]
        breakout = row["High"] > row_prev["High"] and row["Close"] > row_prev["High"]

        if touch_prev and breakout:
            entry_price = row["High"]
            sl = row_prev["Low"]  # SL below swing low (support candle)
            risk = entry_price - sl
            if risk <= 0:
                continue
            target = entry_price + risk * risk_rr

            in_trade = True
            entry_date = row["Date"]

            signals.append({
                "entry_date": entry_date,
                "entry_price": entry_price,
                "sl": sl,
                "target": target,
                "risk": risk,
                "RR": risk_rr,
                "exit_date": None,
                "exit_price": None,
                "exit_reason": None,
                "pnl": None
            })

    return df, pd.DataFrame(signals)


# ----------------- Streamlit app -----------------

st.title("Siddharth‑style 44 MA Swing Strategy (Demo)")

st.write(
    "Upload daily OHLC data (CSV) and this app will apply a simple "
    "44‑MA + 200‑MA swing strategy and show generated trades."
)

uploaded_file = st.file_uploader("Upload daily data CSV", type=["csv"])
risk_rr = st.number_input("Target Reward‑to‑Risk (R:R)", value=3.0, min_value=1.0, step=0.5)

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)

    try:
        full_df, trades_df = compute_ma_signals(df, risk_rr=risk_rr)
    except Exception as e:
        st.error(f"Error: {e}")
    else:
        st.subheader("Data preview")
        st.dataframe(full_df.head(), use_container_width=True)

        if trades_df.empty:
            st.warning("No trades found with current rules / data length.")
        else:
            # Sort trades by entry date
            trades_df = trades_df.sort_values("entry_date").reset_index(drop=True)

            st.subheader("Generated Swing Trades")
            st.dataframe(trades_df, use_container_width=True)

            # Basic stats
            closed = trades_df.dropna(subset=["exit_price"])
            if not closed.empty:
                closed["pnl_pct"] = (closed["pnl"] / closed["entry_price"]) * 100
                total_trades = len(closed)
                wins = (closed["pnl"] > 0).sum()
                winrate = wins / total_trades * 100
                avg_pnl_pct = closed["pnl_pct"].mean()

                st.markdown(
                    f"- Total closed trades: **{total_trades}**\n"
                    f"- Win rate: **{winrate:.1f}%**\n"
                    f"- Avg P&L % per trade: **{avg_pnl_pct:.2f}%**"
                )

            # Download trades
            csv = trades_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download trades CSV",
                data=csv,
                file_name="44MA_swing_trades.csv",
                mime="text/csv",
            )
