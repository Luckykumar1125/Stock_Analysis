# indian_indices.py
import yfinance as yf
import pandas as pd
from typing import List, Dict

def fetch_live_indices() -> Dict:
    """
    Fetches real-time-like data for key Indian stock market indices.
    Returns a dictionary with index data.
    """

    INDIAN_INDICES = {
        "^NSEI": "Nifty 50",
        "^BSESN": "BSE Sensex",
        "^NSEBANK": "Nifty Bank", 
        "^CNXIT": "Nifty IT",
    }

    result = {}

    for symbol, name in INDIAN_INDICES.items():
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d", interval="1m")

            if data.empty:
                print(f"No data found for {symbol}")
                continue

            data.reset_index(inplace=True)

            chart_data = [
                {
                    "timestamp": int(row["Datetime"].timestamp()),
                    "open": row["Open"],
                    "high": row["High"],
                    "low": row["Low"],
                    "close": row["Close"],
                    "volume": row["Volume"],
                }
                for _, row in data.iterrows()
            ]

            result[symbol] = {"name": name, "data": chart_data}

        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")
            continue

    return result
