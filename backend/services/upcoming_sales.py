import os
import json
import requests
import re,time
import concurrent.futures
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field
from groq import Groq

# ---------------------------------------------------------
# 1. Pydantic Models
# ---------------------------------------------------------

class SaleEvent(BaseModel):
    store_name: str = Field(..., description="e.g. Amazon, Flipkart")
    sale_name: str = Field(..., description="e.g. Big Billion Days")
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    source_url: str
    confidence: float

class SalesResponse(BaseModel):
    sales: List[SaleEvent]
    last_updated: str
    source: str 

# ---------------------------------------------------------
# 2. Fallback Data (Safe Mode)
# ---------------------------------------------------------

def get_fallback_data() -> List[SaleEvent]:
    now = datetime.now()
    year = now.year
    today_str = now.strftime("%Y-%m-%d")
    
    # Standard estimates for Indian Sales
    fallbacks = [
        SaleEvent(store_name="Amazon/Flipkart", sale_name="Republic Day Sale", start_date=f"{year}-01-14", end_date=f"{year}-01-20", source_url="Trend", confidence=0.9),
        SaleEvent(store_name="Flipkart", sale_name="Valentine's Sale", start_date=f"{year}-02-07", end_date=f"{year}-02-14", source_url="Trend", confidence=0.7),
        SaleEvent(store_name="Amazon", sale_name="Holi Sale", start_date=f"{year}-03-10", end_date=f"{year}-03-15", source_url="Trend", confidence=0.7),
        SaleEvent(store_name="Myntra", sale_name="EORS (Summer)", start_date=f"{year}-06-10", end_date=f"{year}-06-16", source_url="Trend", confidence=0.8),
        SaleEvent(store_name="Amazon", sale_name="Prime Day", start_date=f"{year}-07-15", end_date=f"{year}-07-16", source_url="Trend", confidence=0.9),
        SaleEvent(store_name="Flipkart", sale_name="Big Billion Days", start_date=f"{year}-10-08", end_date=f"{year}-10-15", source_url="Trend", confidence=0.95),
    ]
    return [s for s in fallbacks if (s.end_date or "9999") >= today_str]

# ---------------------------------------------------------
# 3. Scraper Logic (Fixed Headers & Search)
# ---------------------------------------------------------

def search_sales_articles(query: str, max_results: int = 5):
    results = []
    print(f"🔍 Searching: '{query}'")

    start = time.time()
    MAX_TIME = 4  # seconds hard limit

    try:
        with DDGS() as ddgs:  # ✅ ensures closure
            # 1. Strict search (past month)
            raw = []
            for r in ddgs.text(query, region="in-en", timelimit="m", max_results=max_results):
                raw.append(r)
                if time.time() - start > MAX_TIME:
                    break

            # 2. Retry loose search if empty
            if not raw:
                print("   ⚠️ Strict search empty. Retrying loose...")
                for r in ddgs.text(query, region="in-en", max_results=max_results):
                    raw.append(r)
                    if len(raw) >= max_results or time.time() - start > MAX_TIME:
                        break

            for r in raw:
                results.append({
                    "href": r.get("href"),
                    "title": r.get("title", "")[:120]
                })

    except Exception as e:
        print(f"⚠️ Search Error: {e}")

    return results
def fetch_page_text(url: str) -> str:
    # UPDATED HEADERS to fix 403 Errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
        'Upgrade-Insecure-Requests': '1'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code != 200: return ""
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        # Clean aggressive junk
        for tag in soup(["script", "style", "nav", "footer", "form", "iframe", "svg", "noscript"]):
            tag.extract()
            
        text = ' '.join(soup.get_text(separator=' ').split())
        return text[:5000] # Limit size for LLM
    except:
        return ""

def extract_sales_with_llm(text: str, url: str) -> List[SaleEvent]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or len(text) < 200: return []

    client = Groq(api_key=api_key)
    today = datetime.now().strftime("%Y-%m-%d")

    # FIX: Removed 'response_format={"type": "json_object"}' to prevent 400 Errors
    prompt = f"""
    Current Date: {today}.
    Identify upcoming 2025/2026 e-commerce sales (Amazon, Flipkart, Myntra, Ajio) or from any other Indian fashion e-commerce company from the text.
    
    Return ONLY a JSON object. No markdown, no explanations.
    Format:
    {{
        "sales": [
            {{ "store": "Amazon", "name": "Republic Day Sale", "start": "2026-01-14", "end": "2026-01-20" }}
        ]
    }}
    
    Rules:
    - Use YYYY-MM-DD format.
    - If date is "Jan 15", assume current/next year properly.
    - Ignore past sales.
    
    TEXT:
    {text}
    """

    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1 # Low temp for consistency
        )
        
        raw_content = completion.choices[0].message.content
        
        # Robust Cleaning (Fixes 400 Bad Request issues)
        clean_content = re.sub(r"```json|```", "", raw_content).strip()
        # Find the first '{' and last '}' to handle any extra text
        start_idx = clean_content.find('{')
        end_idx = clean_content.rfind('}') + 1
        if start_idx != -1 and end_idx != -1:
            clean_content = clean_content[start_idx:end_idx]
            
        data = json.loads(clean_content)
        
        events = []
        for s in data.get("sales", []):
            if s.get("name") and s.get("start"):
                events.append(SaleEvent(
                    store_name=s.get("store", "Unknown"),
                    sale_name=s.get("name"),
                    start_date=s.get("start"),
                    end_date=s.get("end"),
                    source_url=url,
                    confidence=0.9
                ))
        return events
    except Exception as e:
        print(f"LLM Parse Error for {url[:20]}: {e}")
        return []

# ---------------------------------------------------------
# 4. Main Parallel Execution
# ---------------------------------------------------------

def process_single_article(article):
    """Worker for ThreadPool"""
    try:
        text = fetch_page_text(article['href'])
        if text:
            return extract_sales_with_llm(text, article['href'])
    except:
        pass
    return []

def scrape_upcoming_sales() -> SalesResponse:
    all_events = []
    source_type = "Live Web Scrape"
    
    # Dynamic Search
    year = datetime.now().year
    query = f"upcoming online shopping sale dates India {year} amazon flipkart myntra"
    
    articles = search_sales_articles(query, max_results=6)
    
    # Parallel Fetch
    if articles:
        print(f"✅ Processing {len(articles)} articles parallelly...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(process_single_article, articles)
            for res in results:
                if res: all_events.extend(res)

    # Fallback Logic
    fallback = get_fallback_data()
    if not all_events:
        print("⚠️ Live scrape failed. Using Annual Trends.")
        all_events = fallback
        source_type = "Annual Trends Estimate"
    elif len(all_events) < 3:
        print("ℹ️ Mixing Live data with Trends.")
        all_events.extend(fallback)
        source_type = "Hybrid (Live + Trends)"

    # Dedup
    unique = {}
    for e in all_events:
        key = f"{e.store_name.lower()[:5]}-{e.sale_name.lower()[:10]}"
        if key not in unique or e.source_url != "Trend":
            unique[key] = e
            
    final = sorted(list(unique.values()), key=lambda x: x.start_date or "9999")
    
    return SalesResponse(
        sales=final,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source=source_type
    )