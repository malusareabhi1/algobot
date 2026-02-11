import sqlite3
import pandas as pd
import math

DB_NAME = "algo_trading.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

# ---------- TABLE CREATION ----------
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

def create_signal_log_table():
    conn = get_connection()
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

# ---------- UTILITY: SAFE CONVERT ----------
def safe_scalar(val, default=0.0):
    """Convert value to a SQLite-compatible scalar."""
    try:
        # If pandas/NumPy type, convert to Python float/int
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return default
        if isinstance(val, (pd.Series, list, tuple)):
            return float(val.iloc[-1]) if isinstance(val, pd.Series) else float(val[0])
        return float(val)
    except (ValueError, TypeError, IndexError):
        return default

def safe_str(val, default=""):
    """Convert value to string."""
    if val is None:
        return default
    return str(val)

# ---------- INSERT FUNCTIONS ----------
def insert_trade_signal(option_type, spot, signal_time, trending_symbol, expiry, ltp):
    option_type = safe_str(option_type)
    spot = safe_scalar(spot)
    signal_time = safe_str(signal_time)
    trending_symbol = safe_str(trending_symbol)
    expiry = safe_str(expiry)
    ltp = safe_scalar(ltp)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
      INSERT INTO trade_signals
      (option_type, spot, signal_time, trending_symbol, expiry, ltp)
      VALUES (?,?,?,?,?,?)
    """, (option_type, spot, signal_time, trending_symbol, expiry, ltp))
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
    condition = safe_str(condition)
    option_type = safe_str(option_type)
    buy_price = safe_scalar(buy_price)
    stoploss = safe_scalar(stoploss)
    quantity = int(quantity or 0)
    expiry = safe_str(expiry)
    entry_time = safe_str(entry_time)
    message = safe_str(message)
    exit_price = safe_scalar(exit_price)
    status = safe_str(status)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO signal_log
        (condition, option_type, buy_price, stoploss, quantity, expiry, entry_time, message, exit_price, status)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (condition, option_type, buy_price, stoploss, quantity, expiry, entry_time, message, exit_price, status))
    conn.commit()
    conn.close()

# ---------- FETCH FUNCTIONS ----------
def fetch_trade_signals(limit=100):
    conn = get_connection()
    cur = conn.cursor()
    rows = cur.execute("""
        SELECT * FROM trade_signals
        ORDER BY id DESC LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return rows

def fetch_signal_log():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM signal_log ORDER BY id DESC", conn)
    conn.close()
    return df
