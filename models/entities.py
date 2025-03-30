
class Portfolio:
    def __init__(self, portfolio_id: int, user_id: int, name: str):
        self.portfolio_id = portfolio_id
        self.user_id = user_id
        self.name = name
        self.symbols = []

class Symbol:
    def __init__(self, symbol_id: int, portfolio_id: int, ticker: str, sector: str):
        self.symbol_id = symbol_id
        self.portfolio_id = portfolio_id
        self.ticker = ticker
        self.sector = sector
        self.transactions = []
        self.current_data = None

    def get_summary(self):
        total_bought = 0
        total_sold = 0
        total_cost = 0
        shares_bought = 0

        for txn in self.transactions:
            if txn.transaction_type == "Buy":
                shares_bought += txn.shares
                total_cost += txn.shares * txn.price + txn.transaction_cost
                total_bought += txn.shares
            elif txn.transaction_type == "Sell":
                total_sold += txn.shares

        avg_cost = total_cost / shares_bought if shares_bought > 0 else None

        return {
            "bought": total_bought,
            "sold": total_sold,
            "avg_cost": round(avg_cost, 2) if avg_cost else "-",
            "total_cost": round(total_cost, 2)
        }


class Transaction:
    def __init__(self, transaction_id: int, symbol_id: int, transaction_type: str, shares: float,
                 price: float, transaction_cost: float, transaction_date: str):
        self.transaction_id = transaction_id
        self.symbol_id = symbol_id
        self.transaction_type = transaction_type
        self.shares = shares
        self.price = price
        self.transaction_cost = transaction_cost
        self.transaction_date = transaction_date