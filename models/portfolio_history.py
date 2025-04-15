import yfinance as yf
import pandas as pd

def get_portfolio_history(symbols, period="1mo"):
    price_data = {}

    for symbol in symbols:
        try:
            ticker = yf.Ticker(symbol.ticker)
            hist = ticker.history(period=period)
            if hist.empty:
                continue
            price_data[symbol.ticker] = hist['Close']
        except Exception:
            continue

    if not price_data:
        return pd.DataFrame()

    price_df = pd.DataFrame(price_data)
    price_df.index = price_df.index.tz_localize(None)
    share_df = pd.DataFrame(0.0, index=price_df.index, columns=price_df.columns)

    # updates the chart if buy/sell transaction are made
    for symbol in symbols:
        if not symbol.transactions:
            continue
        for txn in symbol.transactions:
            txn_date = pd.to_datetime(txn.transaction_date)
            txn_date = txn_date.tz_localize(None) if txn_date.tzinfo else txn_date
            valid_dates = price_df.index[price_df.index >= txn_date]
            if valid_dates.empty:
                continue
            effective_date = valid_dates[0]
            if txn.transaction_type.lower() == "buy":
                share_df.loc[effective_date:, symbol.ticker] += txn.shares
            elif txn.transaction_type.lower() == "sell":
                share_df.loc[effective_date:, symbol.ticker] -= txn.shares

    value_df = price_df * share_df
    value_df["Total"] = value_df.sum(axis=1)
    return value_df[["Total"]]