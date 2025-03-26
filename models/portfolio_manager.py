from typing import List, Dict, Optional
import datetime
from models.database_manager import DatabaseManager
from models.yfinance_source import YFinanceDataSource
from models.entities import Portfolio, Symbol, Transaction
from models.entities import Symbol


class PortfolioManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.yf = YFinanceDataSource()

    def create_portfolio(self, user_id: int, name: str) -> int:
        return self.db_manager.execute_action(
            "INSERT INTO portfolios (user_id, name) VALUES (?, ?)", (user_id, name)
        )

    def get_user_portfolios(self, user_id: int) -> List[Portfolio]:
        rows = self.db_manager.execute_query(
            "SELECT portfolio_id, user_id, name FROM portfolios WHERE user_id = ?",
            (user_id,)
        )
        return [Portfolio(row[0], row[1], row[2]) for row in rows]

    def get_portfolio_symbols(self, portfolio_id: int) -> List[Symbol]:
        rows = self.db_manager.execute_query(
            "SELECT symbol_id, portfolio_id, ticker, sector FROM symbols WHERE portfolio_id = ?",
            (portfolio_id,)
        )
        symbols = []
        for row in rows:
            s = Symbol(*row)
            s.current_data = self.yf.fetch_data(s.ticker)
            s.transactions = self.get_symbol_transactions(s.symbol_id)
            symbols.append(s)
        return symbols

    def add_symbol(self, portfolio_id: int, ticker: str, sector: str) -> Optional[int]:
        exists = self.db_manager.execute_query(
            "SELECT symbol_id FROM symbols WHERE portfolio_id = ? AND ticker = ?",
            (portfolio_id, ticker)
        )
        if exists:
            return None

        return self.db_manager.execute_action(
            "INSERT INTO symbols (portfolio_id, ticker, sector) VALUES (?, ?, ?)",
            (portfolio_id, ticker, sector)
        )

    def add_transaction(self, symbol_id: int, transaction_type: str, shares: float, price: float,
                        transaction_cost: float, transaction_date: str) -> int:
        return self.db_manager.execute_action(
            "INSERT INTO transactions (symbol_id, transaction_type, shares, price, transaction_cost, transaction_date) VALUES (?, ?, ?, ?, ?, ?)",
            (symbol_id, transaction_type, shares, price, transaction_cost, transaction_date)
        )

    def get_symbol_transactions(self, symbol_id: int) -> List[Transaction]:
        rows = self.db_manager.execute_query(
            "SELECT transaction_id, symbol_id, transaction_type, shares, price, transaction_cost, transaction_date FROM transactions WHERE symbol_id = ?",
            (symbol_id,)
        )
        return [Transaction(*row) for row in rows]

    def get_symbol_by_id(self, symbol_id: int) -> Optional[Symbol]:
        row = self.db_manager.execute_query(
            "SELECT symbol_id, portfolio_id, ticker, sector FROM symbols WHERE symbol_id = ?",
            (symbol_id,)
        )

        if row:
            symbol = Symbol(*row[0])
            symbol.transactions = self.get_symbol_transactions(symbol.symbol_id)
            symbol.current_data = self.yf.fetch_data(symbol.ticker)
            return symbol
        return None


