from typing import List, Dict, Optional
from datetime import datetime
import httpx
import xml.etree.ElementTree as ET
from core.config import settings
import yfinance as yf

class NewsFetcher:
    """Interface for fetching news entries given a query."""
    async def fetch(self, query: str, max_articles: int = 10) -> List[Dict]:
        raise NotImplementedError

class RssNewsFetcher(NewsFetcher):
    """
    Fetches news using Google News RSS search:
    https://news.google.com/rss/search?q={query}
    No API key required. Returns list of dicts with title, link, published, snippet.
    """

    RSS_ENDPOINT = "https://news.google.com/rss/search"

    async def fetch(self, query: str, max_articles: int = 10) -> List[Dict]:
        # Build URL with query
        params = {"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"}
        async with httpx.AsyncClient(headers={"User-Agent": settings.default_user_agent}, timeout=20.0) as client:
            r = await client.get(self.RSS_ENDPOINT, params=params)
            r.raise_for_status()
            return self._parse_rss(r.text, max_articles)

    async def resolve_to_ticker(self, query: str) -> str:
        """
        Try to resolve a company name to a ticker symbol using yfinance.
        If already a valid ticker, return as is.
        If no ticker is found, fallback to the original query.
        """
        try:
            query_upper = query.upper()
            ticker_obj = yf.Ticker(query_upper)
            info = ticker_obj.info

            # ✅ If valid ticker found, return its symbol
            if "symbol" in info and info["symbol"]:
                return info["symbol"]

            # ✅ Otherwise, try Yahoo Finance search API
            search = yf.utils.get_json(f"https://query2.finance.yahoo.com/v1/finance/search?q={query}")
            if search and "quotes" in search and len(search["quotes"]) > 0:
                return search["quotes"][0]["symbol"]

        except Exception as e:
            print(f"[WARN] Could not resolve '{query}' to ticker: {e}")

        # Fallback: use original query (still works for general news search)
        return query
    
    def _parse_rss(self, rss_xml: str, max_articles: int):
        root = ET.fromstring(rss_xml)
        channel = root.find("channel")
        items = channel.findall("item") if channel is not None else []
        parsed = []
        for item in items[:max_articles]:
            title = item.findtext("title")
            link = item.findtext("link")
            pub_date = item.findtext("pubDate")
            description = item.findtext("description")
            # parse pub_date loosely
            try:
                published = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")
            except Exception:
                published = None
            parsed.append({
                "title": title or "",
                "link": link,
                "published": published,
                "snippet": description or "",
            })
        return parsed
