import sqlite3
import streamlit as st
from datetime import datetime
import pandas as pd

DB_NAME = "algo_trading.db"

# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signals(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy TEXT,
        symbol TEXT,
        option_type TEXT,
        signal_type TEXT,
        price REAL,
        time TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        symbol TEXT,
        side TEXT,
        quantity INTEGER,
        price REAL,
        status TEXT,
        time TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS positions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        side TEXT,
        quantity INTEGER,
        entry_price REAL,
        current_price REAL,
        pnl REAL,
        status TEXT,
        entry_time TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exits(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        exit_price REAL,
        reason TEXT,
        pnl REAL,
        exit_time TEXT
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS errors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT,
        error_message TEXT,
        time TEXT
    )""")

    conn.commit()
    conn.close()

# =========================================================
# INSERT FUNCTIONS
# =========================================================

def insert_signal(strategy,symbol,otype,stype,price):
    conn=get_conn()
    conn.execute("INSERT INTO signals VALUES(NULL,?,?,?,?,?,?)",
                (strategy,symbol,otype,stype,price,now()))
    conn.commit()
    conn.close()

def insert_order(order_id,symbol,side,qty,price,status):
    conn=get_conn()
    conn.execute("INSERT INTO orders VALUES(NULL,?,?,?,?,?,?,?)",
                (order_id,symbol,side,qty,price,status,now()))
    conn.commit()
    conn.close()

def insert_position(symbol,side,qty,entry,current,pnl,status):
    conn=get_conn()
    conn.execute("INSERT INTO positions VALUES(NULL,?,?,?,?,?,?,?,?)",
                (symbol,side,qty,entry,current,pnl,status,now()))
    conn.commit()
    conn.close()

def insert_exit(symbol,price,reason,pnl):
    conn=get_conn()
    conn.execute("INSERT INTO exits VALUES(NULL,?,?,?, ?,?)",
                (symbol,price,reason,pnl,now()))
    conn.commit()
    conn.close()

def insert_error(module,msg):
    conn=get_conn()
    conn.execute("INSERT INTO errors VALUES(NULL,?,?,?)",
                (module,msg,now()))
    conn.commit()
    conn.close()

# =========================================================
# FETCH FUNCTIONS
# =========================================================

def fetch(table):
    conn=get_conn()
    df=pd.read_sql(f"SELECT * FROM {table} ORDER BY id DESC",conn)
    conn.close()
    return df

# =========================================================
# UTIL
# =========================================================

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# =========================================================
# STREAMLIT DASHBOARD
# =========================================================

st.set_page_config("Algo Trading Control Panel",layout="wide")
create_tables()

st.title("📊 Algo Trading Control Panel")

menu = st.sidebar.radio("Menu",[
    "Signals",
    "Orders",
    "Positions",
    "Exits",
    "Errors"
])

if menu=="Signals":
    st.subheader("📍 Signals Log")
    st.dataframe(fetch("signals"))

elif menu=="Orders":
    st.subheader("🧾 Orders Log")
    st.dataframe(fetch("orders"))

elif menu=="Positions":
    st.subheader("📌 Live Positions")
    st.dataframe(fetch("positions"))

elif menu=="Exits":
    st.subheader("🚪 Exit History")
    st.dataframe(fetch("exits"))

elif menu=="Errors":
    st.subheader("⚠ Error Logs")
    st.dataframe(fetch("errors"))
