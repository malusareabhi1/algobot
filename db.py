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
