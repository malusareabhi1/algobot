import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

DB_NAME = "trading.db"

# -------------------------
# DATABASE CONNECTION
# -------------------------
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# -------------------------
# CREATE TABLE
# -------------------------
def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        price REAL,
        quantity INTEGER,
        side TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

# -------------------------
# INSERT
# -------------------------
def insert_trade(symbol, price, qty, side):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO trades(symbol,price,quantity,side,time)
        VALUES (?,?,?,?,?)
    """, (symbol, price, qty, side, datetime.now()))

    conn.commit()
    conn.close()

# -------------------------
# READ
# -------------------------
def fetch_trades():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM trades ORDER BY id DESC", conn)
    conn.close()
    return df

# -------------------------
# UPDATE
# -------------------------
def update_trade(trade_id, price):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE trades
        SET price=?
        WHERE id=?
    """, (price, trade_id))

    conn.commit()
    conn.close()

# -------------------------
# DELETE
# -------------------------
def delete_trade(trade_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM trades WHERE id=?", (trade_id,))
    conn.commit()
    conn.close()

# -------------------------
# STREAMLIT UI
# -------------------------
st.set_page_config(page_title="SQLite CRUD", layout="wide")
st.title("📊 Algo Trading Logs - CRUD App")

create_table()

menu = st.sidebar.radio(
    "Menu",
    ["Create Trade", "View Trades", "Update Trade", "Delete Trade"]
)

# -------------------------
# CREATE
# -------------------------
if menu == "Create Trade":
    st.subheader("➕ Insert New Trade")

    symbol = st.text_input("Symbol")
    price = st.number_input("Price", min_value=0.0)
    qty = st.number_input("Quantity", min_value=1, step=1)
    side = st.selectbox("Side", ["BUY", "SELL"])

    if st.button("Save Trade"):
        insert_trade(symbol, price, qty, side)
        st.success("Trade Saved!")

# -------------------------
# READ
# -------------------------
elif menu == "View Trades":
    st.subheader("📄 All Trades")
    df = fetch_trades()
    st.dataframe(df, use_container_width=True)

# -------------------------
# UPDATE
# -------------------------
elif menu == "Update Trade":
    st.subheader("✏️ Update Trade Price")

    trade_id = st.number_input("Trade ID", step=1)
    new_price = st.number_input("New Price", min_value=0.0)

    if st.button("Update"):
        update_trade(trade_id, new_price)
        st.success("Trade Updated!")

# -------------------------
# DELETE
# -------------------------
elif menu == "Delete Trade":
    st.subheader("🗑 Delete Trade")

    trade_id = st.number_input("Trade ID", step=1)

    if st.button("Delete"):
        delete_trade(trade_id)
        st.warning("Trade Deleted!")
