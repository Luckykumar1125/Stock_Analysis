import yfinance as yf
import requests

def get_ticker_from_company(company: str):
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={company}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        data = res.json()

        if "quotes" not in data or len(data["quotes"]) == 0:
            raise Exception("No results found")

        ticker = data["quotes"][0]["symbol"]  # Best match
        return ticker
    except Exception as e:
        raise Exception(f"Ticker search failed: {e}")





