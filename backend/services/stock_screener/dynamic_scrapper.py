import os
import yfinance as yf
from groq import Groq
from yahooquery import search
import json
from typing import List
# -----------------------------
#  LLM FUNCTIONS (Groq API)
# -----------------------------

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def llm_extract_companies(sector: str) -> List[str]:
    """
    Uses an LLM to list major Indian companies in the specified sector.
    The output is strictly a Python list of company names.
    """
    # 1. Use a stronger, instruction-following LLM.
    # Replace "your-strong-instruction-model" with the actual model you intend to use 
    # (e.g., 'gpt-4o', 'llama-3-8b-instruct', 'mixtral-8x7b-instruct', etc.)
    LLM_MODEL = "llama-3.3-70b-versatile" 
    
    prompt = f"""
    Based on their market capitalization and prominence on major Indian stock exchanges (like NSE/BSE), 
    list the top 15 most significant Indian companies operating primarily in the **{sector}** sector.

    You **MUST** return your entire response as a valid, single-line **JSON list** of company names.
    Do not include any introductory text, markdown formatting, or explanations outside the JSON list.

    Example output format:
    ["Reliance Industries", "Infosys", "Tata Consultancy Services", "HDFC Bank"]
    """

    resp = client.chat.completions.create(
        model=LLM_MODEL,
        temperature=0.1,  # Lower temperature for factual, deterministic results
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    content = resp.choices[0].message.content.strip()

    # 2. Use safer parsing (JSON) instead of eval()
    try:
        # Strip potential surrounding markdown if the LLM adds it (e.g., ```json ... ```)
        if content.startswith('```') and content.endswith('```'):
            content = content.split('\n', 1)[1].rsplit('\n', 1)[0]
        
        # Safely parse the JSON list
        companies = json.loads(content)
        
        # Ensure the parsed result is actually a list
        if isinstance(companies, list):
            # Clean up names (e.g., removing extra quotes or leading/trailing spaces)
            return [name.strip().replace('"', '') for name in companies if name.strip()]
        else:
            print("Error: LLM did not return a list.")
            return []
            
    except Exception as e:
        print(f"Error parsing LLM response: {e}")
        print(f"Raw response content: {content}")
        return []


def llm_convert_to_tickers(company_names: list) -> list:
    """
    Converts Indian company names into Yahoo Finance NSE tickers
    using Yahoo Finance search instead of LLM.
    Example: "Sun Pharma" -> "SUNPHARMA.NS"
    """

    tickers = []

    for name in company_names:
        try:
            result = search(name)

            if "quotes" not in result:
                continue

            # Filter only NSE tickers (.NS)
            nse_list = [
                q["symbol"]
                for q in result["quotes"]
                if q.get("exchange") == "NS" or q["symbol"].endswith(".NS")
            ]

            if nse_list:
                tickers.append(nse_list[0])  # take the best match
            else:
                # If nothing found, try cleaning the name and searching again
                cleaned = name.replace("Ltd", "").replace("Limited", "").strip()
                result2 = search(cleaned)

                if "quotes" in result2:
                    nse_list = [
                        q["symbol"]
                        for q in result2["quotes"]
                        if q.get("exchange") == "NS" or q["symbol"].endswith(".NS")
                    ]

                    if nse_list:
                        tickers.append(nse_list[0])

        except Exception:
            continue

    return tickers



# -----------------------------
#  MAIN SCRAPER
# -----------------------------

class DynamicSectorStockScraper:
    def __init__(self, sector: str):
        self.sector = sector

    def search_tickers_by_sector(self):
        """
        Returns list of NSE tickers dynamically created by LLM.
        """
        companies = llm_extract_companies(self.sector)
        if not companies:
            return []

        tickers = llm_convert_to_tickers(companies)
        return tickers

    def fetch_stock_info(self, ticker: str):
        """
        Fetches real stock data using yfinance.
        """
        try:
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

    def get_stocks(self):
        tickers = self.search_tickers_by_sector()

        if not tickers:
            return {
                "status": "failed",
                "sector": self.sector,
                "total_stocks": 0,
                "stocks": [],
                "message": "LLM returned no tickers"
            }

        results = [self.fetch_stock_info(t) for t in tickers]

        return {
            "status": "success",
            "sector": self.sector,
            "total_stocks": len(results),
            "stocks": results
        }


