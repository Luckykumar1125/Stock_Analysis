import os
import json
import requests
from typing import List, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from groq import Groq
from duckduckgo_search import DDGS
from fastapi import FastAPI, HTTPException

# --- CONFIGURATION ---
API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY:
    raise ValueError("Please set your GROQ_API_KEY environment variable.")

client = Groq(api_key=API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

app = FastAPI(title="Universal Sales Scraper API")

# --- 1. PYDANTIC MODELS ---
class SaleEvent(BaseModel):
    company_name: str = Field(..., description="Name of the store or brand")
    sale_title: str = Field(..., description="Title of the sale (e.g. 'Flash Sale', 'Clearance')")
    category: str = Field(..., description="Inferred category (e.g. Tech, Fashion, Home, General)")
    discount: str = Field(..., description="Discount details (e.g. 'Up to 50% off')")
    website_url: str = Field(..., description="Link to the deal")
    end_date: str = Field("Unknown", description="When the sale ends")

class ScrapeResponse(BaseModel):
    total_found: int
    source_urls_visited: List[str]
    sales: List[SaleEvent]

# --- 2. BROAD SEARCH LOGIC ---
def search_general_sales(max_results: int = 5):
    """
    Searches for broad, non-sector specific sales lists.
    """
    current_date = datetime.now().strftime("%B %Y") # e.g., "November 2025"
    
    # These queries target aggregator sites that list deals across ALL categories
    queries = [
        f"best daily deals and active sales list {current_date}",
        f"top clearance sales online active now {current_date}",
        f"verified promo codes and discounts list {current_date} site:generic"
    ]
    
    results = []
    seen_urls = set()
    
    print(f"🌍 Starting broad search for {current_date}...")
    
    with DDGS() as ddgs:
        for q in queries:
            try:
                # Get 2-3 results per query to get a good mix
                hits = ddgs.text(q, max_results=3, timelimit="w") # 'w' = past week for freshness
                for h in hits:
                    if h['href'] not in seen_urls:
                        results.append(h)
                        seen_urls.add(h['href'])
            except Exception as e:
                print(f"Search error for '{q}': {e}")
                
    return results[:max_results]

# --- 3. ROBUST SCRAPER ---
def scrape_content(url: str):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.google.com/'
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove navigational/ad clutter to focus on the article text
        for tag in soup(["script", "style", "nav", "footer", "aside", "iframe", "svg"]):
            tag.extract()
            
        text = soup.get_text(separator=' ')
        clean_text = ' '.join(text.split())
        return clean_text[:12000] # Large context for mixed sales lists
    except Exception:
        return None

# --- 4. AI EXTRACTION (Auto-Categorization) ---
def extract_mixed_sales(text: str, source_url: str) -> List[SaleEvent]:
    prompt = f"""
    You are a deal-finding assistant. The text below contains a list of sales from VARIOUS categories (Tech, Fashion, Home, etc.).
    
    YOUR TASK:
    1. Identify every distinct sale/deal mentioned.
    2. Infer the 'category' for each deal based on the store or items (e.g., 'Nike' -> 'Fashion', 'Dell' -> 'Tech').
    3. Extract the discount amount and end date.
    4. If the text doesn't provide a specific link, use the source URL: {source_url}
    
    OUTPUT FORMAT:
    Return valid JSON with a key "sales" containing a list of objects matching this schema:
    {{
        "company_name": "string",
        "sale_title": "string",
        "category": "string",
        "discount": "string",
        "website_url": "string",
        "end_date": "string"
    }}
    
    TEXT CONTENT:
    {text[:12000]}
    """

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a JSON extraction bot. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        
        content = completion.choices[0].message.content
        data = json.loads(content)
        
        valid_sales = []
        for item in data.get("sales", []):
            try:
                # Ensure URL is present
                if "website_url" not in item or not item["website_url"]:
                    item["website_url"] = source_url
                
                valid_sales.append(SaleEvent(**item))
            except Exception:
                continue
                
        return valid_sales

    except Exception as e:
        print(f"AI Extraction Error: {e}")
        return []

# --- 5. ENDPOINT ---


# Run with: uvicorn main:app --reload