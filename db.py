# db.py
import sqlite3

DB_NAME = "algo_trading.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trade_signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        option_type TEXT,
        spot REAL,
        signal_time TEXT,
        trending_symbol TEXT,
        expiry TEXT,
        ltp REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def insert_trade_signal(option_type, spot, signal_time, trending_symbol, expiry, ltp):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO trade_signals
      (option_type, spot, signal_time, trending_symbol, expiry, ltp)
      VALUES (?,?,?,?,?,?)
    """,(option_type, spot, signal_time, trending_symbol, expiry, ltp))
    conn.commit()
    conn.close()

def fetch_trade_signals(limit=100):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT * FROM trade_signals
        ORDER BY id DESC LIMIT ?
    """,(limit,)).fetchall()
    conn.close()
    return rows

def create_signal_log_table():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS signal_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        condition TEXT,
        option_type TEXT,
        buy_price REAL,
        stoploss REAL,
        quantity INTEGER,
        expiry TEXT,
        entry_time TEXT,
        message TEXT,
        exit_price REAL,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

def insert_signal_log(
        condition,
        option_type,
        buy_price,
        stoploss,
        quantity,
        expiry,
        entry_time,
        message,
        exit_price,
        status
    ):

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO signal_log
        (condition,option_type,buy_price,stoploss,quantity,expiry,entry_time,message,exit_price,status)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """,(
        condition,
        option_type,
        buy_price,
        stoploss,
        quantity,
        expiry,
        entry_time,
        message,
        exit_price,
        status
    ))

    conn.commit()
    conn.close()
import pandas as pd

def fetch_signal_log():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql("SELECT * FROM signal_log ORDER BY id DESC", conn)
    conn.close()
    return df

