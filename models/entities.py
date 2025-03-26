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
