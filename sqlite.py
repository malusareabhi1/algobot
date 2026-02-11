import sqlite3
from datetime import datetime

DB_NAME = "trading.db"

# -------------------------------
# CONNECT DATABASE
# -------------------------------
def get_connection():
    return sqlite3.connect(DB_NAME)


# -------------------------------
# CREATE TABLE
# -------------------------------
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
    print("✅ Table Ready")


# -------------------------------
# CREATE (INSERT)
# -------------------------------
def insert_trade(symbol, price, quantity, side):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO trades(symbol,price,quantity,side,time)
    VALUES (?,?,?,?,?)
    """, (symbol, price, quantity, side, datetime.now()))

    conn.commit()
    conn.close()
    print("✅ Trade Inserted")


# -------------------------------
# READ (FETCH)
# -------------------------------
def fetch_trades():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM trades")
    rows = cur.fetchall()

    conn.close()
    return rows


# -------------------------------
# UPDATE
# -------------------------------
def update_trade(trade_id, new_price):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    UPDATE trades
    SET price = ?
    WHERE id = ?
    """, (new_price, trade_id))

    conn.commit()
    conn.close()
    print("✅ Trade Updated")


# -------------------------------
# DELETE
# -------------------------------
def delete_trade(trade_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    conn.commit()
    conn.close()
    print("✅ Trade Deleted")


# -------------------------------
# MAIN PROGRAM
# -------------------------------
if __name__ == "__main__":

    create_table()

    while True:
        print("\n--- MENU ---")
        print("1. Insert Trade")
        print("2. View Trades")
        print("3. Update Trade Price")
        print("4. Delete Trade")
        print("5. Exit")

        choice = input("Enter choice: ")

        if choice == "1":
            sym = input("Symbol: ")
            price = float(input("Price: "))
            qty = int(input("Quantity: "))
            side = input("Side (BUY/SELL): ")
            insert_trade(sym, price, qty, side)

        elif choice == "2":
            trades = fetch_trades()
            print("\n--- Trades ---")
            for t in trades:
                print(t)

        elif choice == "3":
            tid = int(input("Trade ID: "))
            new_price = float(input("New Price: "))
            update_trade(tid, new_price)

        elif choice == "4":
            tid = int(input("Trade ID: "))
            delete_trade(tid)

        elif choice == "5":
            print("👋 Exit")
            break

        else:
            print("❌ Invalid Choice")
