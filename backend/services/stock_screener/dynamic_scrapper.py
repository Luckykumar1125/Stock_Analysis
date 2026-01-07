import os
import yfinance as yf
from groq import Groq
from yahooquery import search
import json
from typing import List
import concurrent.futures
import time

# -----------------------------
#  LLM FUNCTIONS (Groq API)
# -----------------------------

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def llm_extract_companies(sector: str) -> List[str]:
    """
    Uses an LLM to list major Indian companies in the specified sector.
    """
    LLM_MODEL = "llama-3.3-70b-versatile" 
    
    prompt = f"""
    Based on their market capitalization and prominence on major Indian stock exchanges (like NSE/BSE), 
    list the  most significant Indian companies operating primarily in the **{sector}** sector.

    You **MUST** return your entire response as a valid, single-line **JSON list** of company names.
    Do not include any introductory text, markdown formatting, or explanations outside the JSON list.

    Example output format:
    ["Reliance Industries", "Infosys", "Tata Consultancy Services", "HDFC Bank"]
    """

    try:
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            temperature=0.1, 
            messages=[{"role": "user", "content": prompt}]
        )
        content = resp.choices[0].message.content.strip()
        
        if content.startswith('```') and content.endswith('```'):
            content = content.split('\n', 1)[1].rsplit('\n', 1)[0]
        
        companies = json.loads(content)
        if isinstance(companies, list):
            return [name.strip().replace('"', '') for name in companies if name.strip()]
        return []
            
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        return []

# -----------------------------
#  HELPER FUNCTIONS (Now optimized)
# -----------------------------

def resolve_single_ticker(name: str):
    """
    Helper function to resolve a SINGLE ticker. 
    We isolate this so we can run it in parallel.
    """
    try:
        # Search Yahoo Finance
        result = search(name)
        if "quotes" not in result:
            return None

        # Filter for NSE tickers
        nse_list = [
            q["symbol"] for q in result["quotes"]
            if q.get("exchange") == "NS" or q["symbol"].endswith(".NS")
        ]

        if nse_list:
            return nse_list[0]
        
        # Fallback: Clean name and retry
        cleaned = name.replace("Ltd", "").replace("Limited", "").strip()
        result2 = search(cleaned)
        if "quotes" in result2:
            nse_list = [
                q["symbol"] for q in result2["quotes"]
                if q.get("exchange") == "NS" or q["symbol"].endswith(".NS")
            ]
            if nse_list:
                return nse_list[0]
    except Exception:
        return None
    return None

def llm_convert_to_tickers_parallel(company_names: list) -> list:
    """
    Converts names to tickers in PARALLEL.
    """
    tickers = []
    # Use ThreadPool to run searches concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all search tasks
        future_to_name = {executor.submit(resolve_single_ticker, name): name for name in company_names}
        
        for future in concurrent.futures.as_completed(future_to_name):
            result = future.result()
            if result:
                tickers.append(result)
    
    return tickers

def fetch_single_stock_info(ticker: str):
    """
    Fetches info for a SINGLE ticker. Isolated for parallel execution.
    """
    try:
        # yfinance .info is a blocking network call
        info = yf.Ticker(ticker).info
        return {
            "ticker": ticker,
            "company": info.get("shortName"),
            "price": info.get("currentPrice"),
            "change": info.get("regularMarketChange"),
            "change_percent": info.get("regularMarketChangePercent"),
            "market_cap": info.get("marketCap"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "volume": info.get("volume"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}

# -----------------------------
#  MAIN SCRAPER
# -----------------------------

class DynamicSectorStockScraper:
    def __init__(self, sector: str):
        self.sector = sector

    def search_tickers_by_sector(self):
        companies = llm_extract_companies(self.sector)
        if not companies:
            return []
        # UPDATED: Call the parallel version
        return llm_convert_to_tickers_parallel(companies)

    def get_stocks(self):
        start_time = time.time()
        tickers = self.search_tickers_by_sector()

        if not tickers:
            return {
                "status": "failed",
                "sector": self.sector,
                "message": "LLM returned no tickers"
            }

        print(f"Fetching data for {len(tickers)} tickers in parallel...")

        # UPDATED: Fetch stock info in parallel
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {executor.submit(fetch_single_stock_info, t): t for t in tickers}
            
            for future in concurrent.futures.as_completed(future_to_ticker):
                data = future.result()
                results.append(data)

        end_time = time.time()
        print(f"Time taken: {end_time - start_time:.2f} seconds")

        return {
            "status": "success",
            "sector": self.sector,
            "total_stocks": len(results),
            "stocks": results
        }

# Usage Example
if __name__ == "__main__":
    scraper = DynamicSectorStockScraper("Banking")
    print(json.dumps(scraper.get_stocks(), indent=2))