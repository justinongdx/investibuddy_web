from typing import List, Dict, Optional
import datetime
from models.database_manager import DatabaseManager
from models.yfinance_source import YFinanceDataSource
from models.entities import Portfolio, Symbol, Transaction
from models.entities import Symbol
import yfinance as yf
import pandas as pd

def get_portfolio_history(symbols, period='1mo', interval='1d'):
    df_list = []

    for symbol in symbols:
        current_shares = 0
        for txn in symbol.transactions:
            if txn.transaction_type.lower() == "buy":
                current_shares += txn.shares
            elif txn.transaction_type.lower() == "sell":
                current_shares -= txn.shares

        if current_shares <= 0:
            continue  # skip symbols with no holdings

        try:
            hist = yf.download(symbol.ticker, period=period, interval=interval, progress=False)
            if not hist.empty:
                hist['Value'] = hist['Close'] * current_shares
                df_list.append(hist[['Value']].rename(columns={'Value': symbol.ticker}))
        except Exception as e:
            print(f"Error fetching data for {symbol.ticker}: {e}")

    if df_list:
        merged_df = pd.concat(df_list, axis=1).fillna(0)
        merged_df['Total'] = merged_df.sum(axis=1)
        return merged_df[['Total']]
    else:
        return pd.DataFrame()


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

    def calculate_sector_exposure(self, portfolio_id: int) -> dict:
        symbols = self.get_portfolio_symbols(portfolio_id)
        exposure = {}

        # Calculate total portfolio value by summing symbol metrics
        total_value = 0
        symbol_metrics = {}

        for s in symbols:
            metrics = self.calculate_symbol_metrics(s)
            symbol_metrics[s.ticker] = metrics
            total_value += metrics["current_value"]

        if total_value == 0:
            return {}

        for s in symbols:
            sector = s.sector or "Unknown"
            value = symbol_metrics[s.ticker]["current_value"]
            if sector not in exposure:
                exposure[sector] = value
            else:
                exposure[sector] += value

        for sector in exposure:
            value = exposure[sector]
            exposure[sector] = {
                "value": round(value, 2),
                "percentage": round((value / total_value) * 100, 2)
            }

        return exposure

    def calculate_portfolio_metrics(self, portfolio_id: int) -> Dict:
        symbols = self.get_portfolio_symbols(portfolio_id)
        total_investment = 0
        total_current_value = 0
        total_realised_pl = 0
        unrealised_pl_percent = 0
        symbol_metrics = []

        # Calculating metrics for each symbol
        for symbol in symbols:
            symbol_metric = self.calculate_symbol_metrics(symbol)
            symbol_metrics.append(symbol_metric)
            total_investment += symbol_metric["total_investment"]
            total_current_value += symbol_metric["current_value"]
            total_realised_pl += symbol_metric["realised_pl"]

        active_investment = sum(symbol["current_shares"] * symbol["avg_cost"] for symbol in symbol_metrics if
                                symbol["current_shares"] > 0)
        if active_investment > 0:
            unrealised_pl_percent = ((total_current_value - active_investment) / active_investment * 100)

        portfolio_metrics = {
            "total_investment": total_investment,
            "total_current_value": total_current_value,
            "total_unrealised_pl": total_current_value - active_investment,
            "total_unrealised_pl_percent": unrealised_pl_percent,
            "total_realised_pl": total_realised_pl,
            "symbols": symbol_metrics
        }
        return portfolio_metrics

    def calculate_symbol_metrics(self, symbol):
        current_price = symbol.current_data.get("last_price",
                                                0) if symbol.current_data and "error" not in symbol.current_data else 0
        total_shares = 0
        total_investment = 0
        total_sold_amount = 0
        total_sold_shares = 0

        for txn in symbol.transactions:
            if txn.transaction_type.lower() == "buy":
                total_shares += txn.shares
                total_investment += (txn.shares * txn.price) + txn.transaction_cost
            elif txn.transaction_type.lower() == "sell":
                total_sold_shares += txn.shares
                total_sold_amount += (txn.shares * txn.price) - txn.transaction_cost

        current_shares = total_shares - total_sold_shares
        current_shares = max(current_shares, 0)
        avg_cost = total_investment / total_shares if total_shares > 0 else 0
        avg_cost = avg_cost if current_shares > 0 else 0

        # Realised P/L
        realised_pl = 0
        if total_sold_shares > 0:
            avg_cost_per_share = total_investment / total_shares if total_shares > 0 else 0
            realised_pl = total_sold_amount - (total_sold_shares * avg_cost_per_share)

        current_value = current_shares * current_price
        unrealised_pl = current_value - (current_shares * avg_cost)

        symbol_metrics = {
            "ticker": symbol.ticker,
            "sector": symbol.sector,
            "current_price": current_price,
            "avg_cost": avg_cost,
            "current_shares": current_shares,
            "total_investment": total_investment,
            "realised_pl": realised_pl,
            "current_value": current_value,
            "unrealised_pl": unrealised_pl,
            "unrealised_pl_percent": (unrealised_pl / (
                        current_shares * avg_cost) * 100) if current_shares > 0 and avg_cost > 0 else 0,
            "day_change": symbol.current_data.get("change",
                                                  0) if symbol.current_data and "error" not in symbol.current_data else 0,
            "day_change_percent": symbol.current_data.get("change_percent",
                                                          0) if symbol.current_data and "error" not in symbol.current_data else 0
        }
        return symbol_metrics

    def get_portfolio_by_id(self, portfolio_id: int) -> Optional[Portfolio]:
        row = self.db_manager.execute_query(
            "SELECT portfolio_id, user_id, name FROM portfolios WHERE portfolio_id = ?",
            (portfolio_id,)
        )
        if row:
            return Portfolio(*row[0])
        return None

    def delete_portfolio(self, portfolio_id: int, user_id: int) -> bool:
        # First check if the portfolio belongs to the user
        rows = self.db_manager.execute_query(
            "SELECT portfolio_id FROM portfolios WHERE portfolio_id = ? AND user_id = ?",
            (portfolio_id, user_id)
        )

        if not rows:
            return False

        try:
            # Get all symbols in the portfolio
            symbols = self.db_manager.execute_query(
                "SELECT symbol_id FROM symbols WHERE portfolio_id = ?",
                (portfolio_id,)
            )

            # Delete all transactions for each symbol
            for symbol in symbols:
                symbol_id = symbol[0]
                self.db_manager.execute_action(
                    "DELETE FROM transactions WHERE symbol_id = ?",
                    (symbol_id,)
                )

            # Delete all symbols in the portfolio
            self.db_manager.execute_action(
                "DELETE FROM symbols WHERE portfolio_id = ?",
                (portfolio_id,)
            )

            # Finally, delete the portfolio itself
            self.db_manager.execute_action(
                "DELETE FROM portfolios WHERE portfolio_id = ?",
                (portfolio_id,)
            )

            return True
        except Exception as e:
            print(f"Error deleting portfolio: {e}")
            return False

def calculate_portfolio_summary(symbols: list, manager=None):
    if manager is None:
        from models.portfolio_manager import PortfolioManager
        from models.database_manager import DatabaseManager
        manager = PortfolioManager(DatabaseManager("portfolio_manager.db"))

    market_value = 0
    total_cost = 0

    for symbol in symbols:
        metrics = manager.calculate_symbol_metrics(symbol)
        market_value += metrics['current_value']
        total_cost += metrics['current_shares'] * metrics['avg_cost']

    return {
        "market_value": round(market_value, 2),
        "total_cost": round(total_cost, 2),
        "pnl": round(market_value - total_cost, 2)
    }