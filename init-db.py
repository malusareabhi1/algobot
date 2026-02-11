import sqlite3

DB_NAME = "algo_trading.db"

def create_connection():
    return sqlite3.connect(DB_NAME)

def create_tables():
    conn = create_connection()
    cur = conn.cursor()

    # ---------------------------
    # SIGNALS TABLE
    # ---------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        strategy TEXT,
        symbol TEXT,
        option_type TEXT,
        signal_type TEXT,
        price REAL,
        time TEXT
    )
    """)

    # ---------------------------
    # ORDERS TABLE
    # ---------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT,
        symbol TEXT,
        side TEXT,
        quantity INTEGER,
        price REAL,
        status TEXT,
        time TEXT
    )
    """)

    # ---------------------------
    # POSITIONS TABLE
    # ---------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        side TEXT,
        quantity INTEGER,
        entry_price REAL,
        current_price REAL,
        pnl REAL,
        status TEXT,
        entry_time TEXT
    )
    """)

    # ---------------------------
    # EXIT LOGS
    # ---------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS exits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT,
        exit_price REAL,
        reason TEXT,
        pnl REAL,
        exit_time TEXT
    )
    """)

    # ---------------------------
    # ERROR LOGS
    # ---------------------------
    cur.execute("""
    CREATE TABLE IF NOT EXISTS errors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module TEXT,
        error_message TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()
    print("✅ Algo Trading Database Created Successfully")

if __name__ == "__main__":
    create_tables()
