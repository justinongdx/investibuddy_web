import yfinance as yf
import pandas as pd
from collections import defaultdict

def get_portfolio_history(symbols, period="1mo"):
    """
    Fetch historical portfolio value data over a given period.

    Args:
        symbols (List[Symbol]): List of Symbol objects with transactions.
        period (str): Period string (e.g., "1d", "5d", "1mo", "3mo", etc.).

    Returns:
        pd.DataFrame: Date-indexed dataframe with portfolio value.
    """
    price_data = {}
    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol.ticker)
            hist = ticker.history(period=period)
            price_data[symbol.ticker] = hist['Close']
        except Exception:
            continue

    price_df = pd.DataFrame(price_data)

    # Remove timezone from index
    date_index = [pd.Timestamp(date).tz_localize(None) for date in price_df.index]

    # Calculate current and historical share quantities for each day
    share_ledger = defaultdict(lambda: [0]*len(price_df))

    for symbol in symbols:
        for txn in symbol.transactions:
            txn_date = pd.to_datetime(txn.transaction_date).tz_localize(None)
            for idx, date in enumerate(date_index):
                if date >= txn_date:
                    if txn.transaction_type.lower() == "buy":
                        share_ledger[symbol.ticker][idx] += txn.shares
                    elif txn.transaction_type.lower() == "sell":
                        share_ledger[symbol.ticker][idx] -= txn.shares

    for ticker, shares in share_ledger.items():
        price_df[ticker] = price_df[ticker] * shares

    price_df["Total"] = price_df.sum(axis=1)
    return price_df

