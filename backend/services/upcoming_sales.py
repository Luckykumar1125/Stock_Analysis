import os
import json
import requests
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field
from groq import Groq

# --- Pydantic Models ---

class SaleEvent(BaseModel):
    store_name: str = Field(..., description="e.g. Amazon, Flipkart, Myntra, Ajio")
    sale_name: str = Field(..., description="e.g. Big Billion Days, End of Reason Sale")
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD or null")
    end_date: Optional[str] = Field(None, description="YYYY-MM-DD or null")
    source_url: str
    confidence: float

class SalesResponse(BaseModel):
    sales: List[SaleEvent]
    last_updated: str
    source: str 

# --- Expanded Fallback Data ---
def get_fallback_data() -> List[SaleEvent]:
    """
    Returns a comprehensive list of standard annual sales in India.
    Used when live scraping fails or returns too few results.
    """
    current_year = datetime.now().year
    next_year = current_year + 1
    
    # A much larger list of standard recurring sales
    fallbacks = [
        # Late 2024 / Early 2025
        SaleEvent(store_name="Amazon/Flipkart", sale_name="Black Friday Sale", start_date=f"{current_year}-11-24", end_date=f"{current_year}-11-28", source_url="Annual Trend", confidence=0.6),
        SaleEvent(store_name="Myntra", sale_name="End of Reason Sale (EORS)", start_date=f"{current_year}-12-09", end_date=f"{current_year}-12-15", source_url="Annual Trend", confidence=0.8),
        SaleEvent(store_name="Amazon/Flipkart", sale_name="Christmas & Year End Sale", start_date=f"{current_year}-12-20", end_date=f"{current_year}-12-28", source_url="Annual Trend", confidence=0.7),
        
        # 2025
        SaleEvent(store_name="Amazon/Flipkart", sale_name="Republic Day Sale", start_date=f"{next_year}-01-14", end_date=f"{next_year}-01-20", source_url="Annual Trend", confidence=0.9),
        SaleEvent(store_name="Flipkart", sale_name="Valentine's Day Sale", start_date=f"{next_year}-02-07", end_date=f"{next_year}-02-14", source_url="Annual Trend", confidence=0.6),
        SaleEvent(store_name="Amazon", sale_name="Holi Sale", start_date=f"{next_year}-03-10", end_date=f"{next_year}-03-15", source_url="Annual Trend", confidence=0.6),
        SaleEvent(store_name="Ajio", sale_name="Big Bold Sale", start_date=f"{next_year}-03-20", end_date=f"{next_year}-03-25", source_url="Annual Trend", confidence=0.5),
        SaleEvent(store_name="Amazon/Flipkart", sale_name="Summer Sale", start_date=f"{next_year}-05-04", end_date=f"{next_year}-05-10", source_url="Annual Trend", confidence=0.7),
        SaleEvent(store_name="Myntra", sale_name="EORS (Summer Edition)", start_date=f"{next_year}-06-10", end_date=f"{next_year}-06-17", source_url="Annual Trend", confidence=0.8),
        SaleEvent(store_name="Amazon", sale_name="Prime Day", start_date=f"{next_year}-07-15", end_date=f"{next_year}-07-16", source_url="Annual Trend", confidence=0.9),
        SaleEvent(store_name="Flipkart", sale_name="Big Billion Days", start_date=f"{next_year}-10-08", end_date=f"{next_year}-10-15", source_url="Annual Trend", confidence=0.95),
    ]
    
    # Filter: Only show sales that haven't ended yet (or ended very recently)
    today = datetime.now().strftime("%Y-%m-%d")
    future_sales = []
    for sale in fallbacks:
        # Include if end_date is in future OR if start_date is in future
        if sale.end_date >= today or (sale.start_date and sale.start_date >= today):
            future_sales.append(sale)
            
    return future_sales

# --- Scraper Logic ---

def search_sales_articles(query: str, max_results: int = 8): # <--- INCREASED TO 8
    results = []
    try:
        ddgs = DDGS()
        # 'm' = past month. Ensuring freshness.
        search_results = ddgs.text(query, region='in-en', timelimit='m', max_results=max_results)
        if search_results:
            for r in search_results:
                results.append({"href": r['href'], "title": r['title']})
    except Exception as e:
        print(f"Search Warning: {e}")
    return results

def fetch_page_text(url: str) -> str:
    # Rotated User Agents to avoid detection
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=6) # Fast timeout to keep overall speed up
        if resp.status_code != 200: return ""
        
        soup = BeautifulSoup(resp.content, 'html.parser')
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "svg"]):
            tag.extract()
            
        text = soup.get_text(separator=' ')
        clean_text = ' '.join(text.split())
        # Increased character limit slightly to capture longer lists
        return clean_text[:10000] 
    except:
        return ""

def extract_sales_with_llm(text: str, url: str) -> List[SaleEvent]:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or len(text) < 200: return []

    client = Groq(api_key=api_key)
    today = datetime.now().strftime("%Y-%m-%d")

    # Prompt optimized for finding lists of sales
    prompt = f"""
    Today is {today}. 
    Analyze the text and extract ALL upcoming e-commerce sales events (Amazon, Flipkart, Myntra, Ajio, Tata Cliq).
    Look for tables or lists of dates in the text.
    
    Return JSON: {{ "sales": [ {{ "store_name": "...", "sale_name": "...", "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }} ] }}
    
    Rules:
    1. If multiple sales are listed, capture ALL of them.
    2. If a sale says "Coming Soon" or date is unclear, omit it.
    3. Prioritize CONFIRMED dates over expected ones.

    TEXT:
    {text}
    """

    try:
        completion = client.chat.completions.create(
            model="llama3-70b-8192", 
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        data = json.loads(completion.choices[0].message.content)
        
        events = []
        for s in data.get("sales", []):
            if s.get("sale_name") and s.get("store_name"):
                start = s.get("start_date")
                # Basic validation: Must have a start date to be useful
                if start and len(start) == 10: 
                    events.append(SaleEvent(
                        store_name=s["store_name"],
                        sale_name=s["sale_name"],
                        start_date=start,
                        end_date=s.get("end_date"),
                        source_url=url,
                        confidence=0.9
                    ))
        return events
    except Exception as e:
        print(f"LLM Error: {e}")
        return []

def scrape_upcoming_sales() -> SalesResponse:
    all_events = []
    source_type = "Live Web Scrape"
    
    # 1. Search: Increased limit and added 'fashion' to query to get Myntra/Ajio
    print("🔍 Searching for sales...")
    articles = search_sales_articles("upcoming online shopping sale dates India 2025 amazon flipkart myntra news", max_results=6)
    
    # 2. Scrape Loop
    if articles:
        for article in articles:
            print(f"📄 Scanning: {article['title'][:40]}...")
            text = fetch_page_text(article['href'])
            if text:
                events = extract_sales_with_llm(text, article['href'])
                all_events.extend(events)
    
    # 3. Fallback & Augmentation
    # Even if we find some live sales, we might want to append far-future sales from our hardcoded list
    # if the live scrape only found 1 or 2 items.
    fallback_events = get_fallback_data()
    
    if not all_events:
        print("⚠️ No live data found. Using fallback.")
        all_events = fallback_events
        source_type = "Annual Trends Estimate"
    elif len(all_events) < 3:
        # If we found < 3 live sales, mix in the fallback data to make the list look full
        print("ℹ️ Low live data. Mixing with trends.")
        all_events.extend(fallback_events)
        source_type = "Hybrid (Live + Trends)"

    # 4. Dedup & Sort
    unique_events = {}
    for e in all_events:
        # Normalize keys to avoid "Big Billion Day" vs "Big Billion Days" duplicates
        key = f"{e.store_name.lower().split()[0]}-{e.sale_name.lower()[:10]}"
        if key not in unique_events:
            unique_events[key] = e
            
    # Convert back to list and Sort by start_date
    final_list = list(unique_events.values())
    final_list.sort(key=lambda x: x.start_date if x.start_date else "9999-99-99")

    return SalesResponse(
        sales=final_list,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        source=source_type
    )