import yfinance as yf

class YFinanceDataSource:
    def fetch_data(self, ticker: str, period: str = "1d") -> dict:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            history = stock.history(period=period)

            last_price = info.get("currentPrice") or info.get("previousClose")
            if last_price is None and not history.empty:
                last_price = history["Close"].iloc[-1]
            if last_price is None:
                return {"error": f"⚠️ No price data found for {ticker}"}

            return {
                "ticker": ticker,
                "company_name": info.get("shortName", "N/A"),
                "sector": info.get("sector", "N/A"),
                "last_price": last_price,
                "change": last_price - info.get("previousClose", last_price),
                "change_percent": ((last_price - info.get("previousClose", last_price)) / info.get("previousClose", last_price)) * 100 if info.get("previousClose") else 0,
                "market_time": history.index[-1].strftime("%Y-%m-%d %H:%M:%S") if not history.empty else "N/A",
                "market_cap": info.get("marketCap", "N/A"),
                "volume": history["Volume"].iloc[-1] if not history.empty else "N/A",
                "high": history["High"].iloc[-1] if not history.empty else "N/A",
                "low": history["Low"].iloc[-1] if not history.empty else "N/A",
                "open": history["Open"].iloc[-1] if not history.empty else "N/A",
                "previous_close": info.get("previousClose", last_price),
            }

        except Exception as e:
            return {"error": f"⚠️ Error fetching data for {ticker}: {str(e)}"}
