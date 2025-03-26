import sqlite3
from typing import Optional

class DatabaseManager:
    def __init__(self, db_name: str = "portfolio_manager.db"):
        self.db_name = db_name

    def get_connection(self):
        return sqlite3.connect(self.db_name)

    def execute_query(self, query: str, params: tuple = None) -> list:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params if params else ())
            result = cursor.fetchall()
            return result
        except sqlite3.OperationalError as e:
            print(f"⚠️ Database error: {e}")
            return []
        finally:
            conn.close()

    def execute_action(self, query: str, params: tuple = None) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params if params else ())
            last_id = cursor.lastrowid
            conn.commit()
            return last_id
        except sqlite3.OperationalError as e:
            print(f"⚠️ Database error: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()

def create_database():
    conn = sqlite3.connect("portfolio_manager.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        risk_tolerance TEXT CHECK(risk_tolerance IN ('Low', 'Medium', 'High')) NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolios (
        portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS symbols (
        symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
        portfolio_id INTEGER NOT NULL,
        ticker TEXT NOT NULL,
        sector TEXT,
        FOREIGN KEY (portfolio_id) REFERENCES portfolios (portfolio_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,
        shares REAL NOT NULL,
        price REAL NOT NULL,
        transaction_cost REAL NOT NULL,
        transaction_date TEXT NOT NULL,
        FOREIGN KEY (symbol_id) REFERENCES symbols (symbol_id)
    )
    """)

    conn.commit()
    conn.close()