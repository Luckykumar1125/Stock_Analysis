# fast_stock_assistant.py
import os
import re
import json
import time
import requests
import numpy as np
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv


# Finance libs (keep these as in your original code)
import yfinance as yf
from yahooquery import search

# Embedding / reranking libs
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder


# FastAPI HTTPException for compatibility with your original code
try:
    from fastapi import HTTPException
except Exception:
    class HTTPException(Exception):
        def __init__(self, status_code=500, detail=""):
            super().__init__(f"{status_code}: {detail}")
            self.status_code = status_code
            self.detail = detail

# Try to import your schemas; if not available, define minimal stand-ins.
try:
    from core.schemas import ChatResponse, StockData
except Exception:
    from dataclasses import dataclass

    @dataclass
    class StockData:
        ticker: str
        company_name: Optional[str] = None
        current_price: Optional[float] = None
        previous_close: Optional[float] = None
        market_cap: Optional[float] = None
        currency: Optional[str] = None
        exchange: Optional[str] = None
        price_change: Optional[float] = None
        price_change_percent: Optional[float] = None

    @dataclass
    class ChatResponse:
        answer: str
        query_type: str = "general"
        stock_data: Optional[StockData] = None
        raw_data: Optional[Dict[str, Any]] = None


# Load environment
load_dotenv()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    # We won't raise here to allow module import in dev environment, but runtime functions will check.
    pass

# === EXACT PROMPTS (kept verbatim from your original code) ===
STOCK_INSIGHT_PROMPT_TEXT = """
You are a friendly financial assistant helping beginners understand stocks and investments.
Based on the stock data provided, give a clear, structured, and easy-to-understand analysis.

Structure your response in the following order with bullet points for clarity:

1. Company Overview:
   - Provide a brief description of the company, its industry, and its history.

2. Stock Price Details:
   - Current price
   - Previous close
   - Price change and percentage
   - Market capitalization
   - Currency and exchange

3. Market Trends / Insights:
   - Key observations about price movement
   - Short-term and long-term trends
   - Any notable market factors affecting the stock

4. Beginner-friendly Advice:
   - Practical tips for new investors
   - Portfolio management suggestions
   - Key points to remember about investing in this stock

Strictly follow the following Guidelines:
- Use bullet points for all key information.
- Keep paragraphs short and simple.
- Do NOT use ** or __.
- Use markdown format.
- Make it concise, encouraging, and beginner-friendly.
"""

GENERAL_FINANCE_PROMPT_TEXT = """
You are a friendly financial advisor helping beginners learn about finance, investing, and markets. 
Provide clear, structured, and easy-to-understand responses for any finance-related question. 
If the user asks about a specific company or stock and you don't have current data, 
provide general investment advice and explain concepts clearly.

Structure your response in the following order with bullet points for clarity:

1. Overview:
   - Give a brief introduction to the topic or financial concept.

2. Key Details / Insights:
   - Explain important points, examples, or definitions.
   - Use bullet points for each key idea.

3. Practical Advice / Tips:
   - Provide actionable advice for beginners.
   - Include portfolio, investing, or risk management suggestions where relevant.

Strictly follow the following Guidelines:
- Use bullet points for all important information.
- Keep paragraphs short, simple, and beginner-friendly.
- Do NOT use ** or __.
- Use markdown format.
- Make the response concise, encouraging, and educational.
"""

# === Groq API call helper (direct call, no LangChain) ===
def call_groq(prompt: str, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct", temperature: float = 0.3) -> str:
    """
    Call Groq API (or compatible endpoint). Returns the assistant text content.
    Ensure GROQ_API_KEY env var is set before calling.
    """
    if not GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY environment variable not set.")

    # NOTE: URL and request spec may need adjustment depending on your provider's API format.
    url = "https://api.groq.com/openai/v1/chat/completions"  # keep as example; adapt if your Groq endpoint differs
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": ""},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 800,
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=f"LLM API error: {resp.text}")

    j = resp.json()
    # adapt to the actual provider response structure
    # For OpenAI-like responses:
    try:
        content = j["choices"][0]["message"]["content"]
    except Exception:
        # fallback: return raw JSON as string (for debug)
        content = json.dumps(j)
    return content


# === Your original helper functions (kept as close as possible) ===

def classify_query(query: str) -> str:
    """Classify if query is about specific stock or general finance"""
    stock_indicators = [
        "stock price", "share price", "ticker", "stock of", "shares of",
        "should i buy", "should i sell", "invest in", "price of"
    ]
    
    query_lower = query.lower()
    
    # Check if it contains company names or stock-specific terms
    if any(indicator in query_lower for indicator in stock_indicators):
        return "stock"
    
    # Check for general finance terms
    finance_terms = [
        "what is", "how does", "explain", "mutual fund", "portfolio",
        "investment", "finance", "market", "trading", "dividend",
        "bonds", "etf", "risk", "return"
    ]
    
    if any(term in query_lower for term in finance_terms):
        return "general"
    
    return "stock"  # Default to stock search


def resolve_query_to_ticker(query: str) -> Optional[str]:
    """
    Extract company name from query and resolve to ticker symbol.
    Prioritize Indian stocks (NSE/BSE), fallback to global stocks.
    """
    try:
        query_lower = query.lower()

        # Remove common stopwords
        stopwords = [
            "stock", "share", "price", "ticker", "value", "company",
            "tell", "me", "about", "the", "of", "what", "is", "how",
            "much", "should", "i", "buy", "sell", "invest", "in"
        ]
        pattern = r"\b(" + "|".join(stopwords) + r")\b"
        clean_query = re.sub(pattern, "", query_lower, flags=re.IGNORECASE).strip()

        if not clean_query:
            clean_query = query

        # Search using YahooQuery
        results = search(clean_query)
        if results and "quotes" in results and results["quotes"]:
            quotes = results["quotes"]

            # Step 1: prioritize NSE/BSE
            indian_stocks = [
                q for q in quotes
                if q.get("exchange") in ["NSE", "BSE", "NSI"]
                and q.get("quoteType") == "EQUITY"
            ]
            if indian_stocks:
                return indian_stocks[0].get("symbol")

            # Step 2: fallback to global stocks
            global_stocks = [
                q for q in quotes
                if q.get("quoteType") == "EQUITY"
            ]
            if global_stocks:
                return global_stocks[0].get("symbol")

        return None

    except Exception as e:
        print(f"Error resolving query '{query}': {e}")
        return None


def fetch_stock_info(ticker_symbol: str) -> Optional[Dict[str, Any]]:
    """Fetches detailed stock data using yfinance (reliable methods)."""
    try:
        ticker = yf.Ticker(ticker_symbol)

        # Use fast_info (more reliable than .info)
        fast_info = getattr(ticker, "fast_info", None) or {}

        # Get recent history
        hist = ticker.history(period="5d")
        
        current_price = None
        previous_close = None
        price_change = None
        price_change_percent = None

        if not hist.empty:
            current_price = hist["Close"].iloc[-1]
            if len(hist) > 1:
                previous_close = hist["Close"].iloc[-2]
                price_change = current_price - previous_close
                price_change_percent = (price_change / previous_close) * 100 if previous_close else None
            else:
                previous_close = fast_info.get("previous_close", current_price)
        else:
            current_price = fast_info.get("last_price")
            previous_close = fast_info.get("previous_close")

        return {
            "ticker": ticker_symbol.upper(),
            "company_name": fast_info.get("longName") or fast_info.get("shortName") or ticker_symbol,
            "current_price": current_price,
            "previous_close": previous_close,
            "market_cap": fast_info.get("market_cap"),
            "currency": fast_info.get("currency", "USD"),
            "exchange": fast_info.get("exchange"),
            "price_change": price_change,
            "price_change_percent": price_change_percent,
        }
    except Exception as e:
        print(f"Error fetching stock info for {ticker_symbol}: {e}")
        return None


# === Embedding + Reranking initialization ===
# You can change models to smaller ones if you need faster, cheaper inference.
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CROSS_ENCODER_MODEL = os.environ.get("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")

_embedding_model = None
_cross_encoder = None

def init_models():
    global _embedding_model, _cross_encoder
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    if _cross_encoder is None:
        _cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL)

# Call at import if desired:
try:
    init_models()
except Exception as e:
    # model download may fail in offline environment; will initialize later when available
    print("Embedding or cross-encoder initialization deferred:", str(e))


# === LLM-based helpers ===

def llm_is_stock_query(query: str) -> bool:
    """
    Validate whether the query is stock-related using LLM.
    Returns True if LLM says YES. Uses a simple YES/NO prompt.
    """
    prompt = f"""
Determine if the following query is related to stock market, trading, finance, or equities. 
Respond only with YES or NO.

Query: {query}
"""
    try:
        resp = call_groq(prompt, temperature=0.0)
        resp = resp.strip().lower()
        return resp.startswith("yes")
    except Exception as e:
        # fallback to rule-based classification
        return classify_query(query) == "stock"


def llm_generate_query_variations(query: str, n: int = 6) -> List[str]:
    """
    Generate diverse rephrasings of the user's query using the LLM.
    Returns a list of variations (may include the original).
    """
    prompt = f"""
Generate {n} diverse rephrasings of the following query. 
Only output a numbered list of rewritten queries.

Query: {query}
"""
    try:
        resp = call_groq(prompt, temperature=0.7)
        variations = re.findall(r"\d+\.\s*(.*)", resp)
        if not variations:
            # fallback: split lines
            lines = [line.strip("- ") for line in resp.splitlines() if line.strip()]
            variations = lines[:n] if lines else [query]
        return variations[:n]
    except Exception as e:
        return [query]


# === Hybrid search across stock data ===

def _text_chunks_from_stock_data(stock_data: Dict[str, Any]) -> List[str]:
    """
    Convert stock_data dict into simple textual chunks.
    You can extend this to more advanced chunking if you have long documents (e.g., filings).
    """
    chunks = []
    for k, v in stock_data.items():
        try:
            # represent nested dicts as JSON string
            if isinstance(v, (dict, list)):
                v_text = json.dumps(v, default=str)
            else:
                v_text = str(v)
        except Exception:
            v_text = str(v)
        chunks.append(f"{k}: {v_text}")
    return chunks


def hybrid_search(stock_data: Dict[str, Any], queries: List[str], top_k: int = 8) -> List[str]:
    """
    Hybrid search: combine vector similarity and simple keyword signal.
    Returns top_k chunks (strings).
    """
    init_models()
    chunks = _text_chunks_from_stock_data(stock_data)
    if not chunks:
        return []

    chunk_embs = _embedding_model.encode(chunks, convert_to_numpy=True)
    results = []

    for q in queries:
        q_emb = _embedding_model.encode(q, convert_to_numpy=True)
        # cosine similarity
        denom = (np.linalg.norm(chunk_embs, axis=1) * np.linalg.norm(q_emb) + 1e-10)
        sim_scores = np.dot(chunk_embs, q_emb) / denom

        # keyword match: proportion of query tokens present
        q_tokens = set(re.findall(r"\w+", q.lower()))
        kw_scores = []
        for c in chunks:
            c_tokens = set(re.findall(r"\w+", c.lower()))
            if not q_tokens:
                kw_scores.append(0.0)
            else:
                kw_scores.append(len(q_tokens & c_tokens) / len(q_tokens))
        kw_scores = np.array(kw_scores)

        final = 0.7 * sim_scores + 0.3 * kw_scores
        for i, score in enumerate(final):
            results.append((chunks[i], float(score)))

    # aggregate by chunk (max score per chunk across variations)
    agg = {}
    for chunk, score in results:
        agg[chunk] = max(agg.get(chunk, 0.0), score)

    sorted_chunks = sorted(agg.items(), key=lambda x: x[1], reverse=True)
    top = [c for c, _ in sorted_chunks[:top_k]]
    return top


# === Cross-encoder re-ranking ===

def rerank_chunks(query: str, chunks: List[str], top_k: int = 5) -> List[str]:
    """
    Use a cross-encoder to rerank the candidate chunks by semantic relevance to the query.
    """
    init_models()
    if not chunks:
        return []
    pairs = [[query, c] for c in chunks]
    try:
        scores = _cross_encoder.predict(pairs)
    except Exception as e:
        # Fallback: simple similarity with embedding model if cross-encoder fails
        chunk_embs = _embedding_model.encode(chunks, convert_to_numpy=True)
        q_emb = _embedding_model.encode(query, convert_to_numpy=True)
        denom = (np.linalg.norm(chunk_embs, axis=1) * np.linalg.norm(q_emb) + 1e-10)
        scores = np.dot(chunk_embs, q_emb) / denom

    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    top_ranked = [c for c, _ in ranked[:top_k]]
    return top_ranked


def get_parent_chunks(chunks: List[str]) -> str:
    """
    For simple metadata chunks parent chunk is itself.
    For richer sources you would expand to include parent documents.
    """
    return "\n\n".join(chunks)


# === Formatting helpers (kept from your original code, lightly adapted) ===

def format_stock_response_to_bullets(text: str) -> str:
    """
    Formats stock response into clean sections with headings and bullet points.
    Removes markdown symbols and keeps paragraphs intact.
    """
    # Remove markdown symbols
    text = text.replace("**", "").replace("_", "")

    # Split by double newlines to get paragraphs
    paragraphs = text.split("\n\n")
    formatted_lines = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Detect section headings
        heading_keywords = ["company overview", "stock price details", 
                            "market trends", "beginner-friendly advice", 
                            "conclusion", "additional tips"]
        if any(para.lower().startswith(word) for word in heading_keywords):
            formatted_lines.append(f"- {para}")
        else:
            # Split by single lines inside paragraph to create bullets
            for line in para.splitlines():
                line = line.strip()
                if line:
                    formatted_lines.append(f"  - {line}")

    return "\n".join(formatted_lines)


def format_stock_response(response_text: str, stock_data: dict) -> str:
    """
    Convert LLM response into structured bullet points with clean formatting.
    """
    # Remove markdown symbols
    cleaned_text = response_text.replace("**", "").replace("_", "").strip()

    # Sections
    company_name = stock_data.get("company_name", stock_data.get("ticker", "Unknown"))
    exchange = stock_data.get("exchange", "N/A")
    currency = stock_data.get("currency", "INR")
    current_price = stock_data.get("current_price", "N/A")
    previous_close = stock_data.get("previous_close", "N/A")
    price_change = stock_data.get("price_change")
    price_change_percent = stock_data.get("price_change_percent")

    sections = [
        "Company Overview:",
        f"- Name: {company_name}",
        f"- Exchange: {exchange}",
        "",
        "Stock Price Details:",
        f"- Current Price: {current_price} {currency}",
        f"- Previous Close: {previous_close} {currency}" if previous_close else "",
    ]

    if price_change is not None and price_change_percent is not None:
        sections.append(f"- Change: {price_change:.2f} {currency} ({price_change_percent:.2f}%)")

    # Market insights and advice
    insights_lines = [line.strip("-* ") for line in cleaned_text.splitlines() if line.strip()]
    if insights_lines:
        sections.append("")
        sections.append("Market Insights / Advice:")
        sections += [f"- {line}" for line in insights_lines]

    return "\n".join(sections)


# === Core pipeline functions ===

def generate_final_stock_answer(user_query: str, stock_data: dict, context: str) -> str:
    """
    Build the final prompt using the STOCK_INSIGHT_PROMPT_TEXT and call the LLM.
    """
    # Attach stock_data as JSON for structured grounding
    stock_json = json.dumps(stock_data, indent=2, default=str)
    prompt = STOCK_INSIGHT_PROMPT_TEXT + "\n\n" + f"User Query: {user_query}\n\nStock Data: {stock_json}\n\nRelevant Context:\n{context}\n\nPlease respond now."
    return call_groq(prompt, temperature=0.3)


def generate_general_finance_answer(user_query: str) -> str:
    prompt = GENERAL_FINANCE_PROMPT_TEXT + f"\n\nUser Query: {user_query}\n\nPlease respond now."
    return call_groq(prompt, temperature=0.3)


# Async-compatible wrappers (your original code used async)
# They are implemented as regular functions but keep async signatures for plug-and-play.
import asyncio

async def process_general_finance_query(query: str) -> ChatResponse:
    try:
        ans = generate_general_finance_answer(query)
        return ChatResponse(answer=ans, query_type="general")
    except Exception as e:
        return ChatResponse(
            answer="I'd be happy to help you learn about finance! However, I'm having trouble generating a detailed response right now.",
            query_type="general"
        )


async def process_stock_query_fast(query: str) -> ChatResponse:
    """
    Full fast pipeline for stock queries, no LangChain.
    """
    # 1. LLM-based validation (fallback to rule-based)
    try:
        is_stock = llm_is_stock_query(query)
    except Exception:
        is_stock = (classify_query(query) == "stock")

    if not is_stock:
        # Treat as general finance question
        return await process_general_finance_query(query)

    # 2. Resolve ticker (keeps your original logic)
    ticker = resolve_query_to_ticker(query)
    if not ticker:
        # fallback to general finance
        return await process_general_finance_query(query)

    # 3. Fetch stock data
    stock_data = fetch_stock_info(ticker)
    if not stock_data:
        return ChatResponse(
            answer=f"I found a ticker '{ticker}' but couldn't retrieve current data. This might be due to market hours or data availability. Would you like general investment information instead?",
            query_type="stock"
        )

    # 4. Generate diverse query variations
    try:
        variations = llm_generate_query_variations(query, n=6)
    except Exception:
        variations = [query]

    # 5. Hybrid search across fetched stock metadata
    try:
        candidates = hybrid_search(stock_data, variations, top_k=8)
    except Exception:
        candidates = _text_chunks_from_stock_data(stock_data)[:8]

    # 6. Re-rank using cross-encoder
    try:
        reranked = rerank_chunks(query, candidates, top_k=5)
    except Exception:
        reranked = candidates[:5]

    # 7. Get parent chunks for top ranked results
    context = get_parent_chunks(reranked)

    # 8. Generate final answer using the same STOCK prompt
    try:
        final_text = generate_final_stock_answer(query, stock_data, context)
        # Optionally format into bullets similar to original function
        formatted = format_stock_response_to_bullets(final_text)
        return ChatResponse(
            answer=formatted,
            stock_data=StockData(**stock_data),
            raw_data=stock_data,
            query_type="stock"
        )
    except Exception as e:
        # Graceful fallback
        fallback = f"I found information about {stock_data.get('company_name', ticker)} but had trouble generating insights. Current price: {stock_data.get('current_price', 'N/A')}."
        return ChatResponse(
            answer=fallback,
            stock_data=StockData(**stock_data),
            raw_data=stock_data,
            query_type="stock"
        )


# === Optional synchronous facade for quick testing ===
def ask(query: str) -> ChatResponse:
    """
    Synchronous helper to run the async pipeline (blocking).
    """
    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(process_stock_query_fast(query))
    except RuntimeError:
        # If there is no running loop in some contexts, create a new one
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        return new_loop.run_until_complete(process_stock_query_fast(query))

