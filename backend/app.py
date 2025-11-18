from fastapi import FastAPI,WebSocket,APIRouter, Depends, HTTPException,Query,UploadFile,File
from core.schemas import APIResponse,MarketInsights,ChatRequest,ChatResponse
from services.news_fetcher import fetch_news
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse,StreamingResponse, Response
from services.charts import fetch_live_indices
from services.finance import process_stock_query_fast
from services.watchlist import get_ticker_from_company
import yfinance as yf
from services.sentiment_analyzer import analyze_sentiment
from core.config import settings
import pandas as pd
from services.balance_sheet_analyzer.parser import BankStatementParser
from storage.db import save_transactions
import shutil
from services.balance_sheet_analyzer.processor_llm import (
    read_transactions_from_db,
    categorize_transactions,
    monthly_spend_summary,
    pie_chart_category,
    bar_chart_top_merchants
)
import os
import base64
from typing import Optional,Dict, Any
from services.stock_screener.dynamic_scrapper import DynamicSectorStockScraper
from pydantic import BaseModel
router = APIRouter()
class SectorRequest(BaseModel):
    sector: str
app = FastAPI(title="Market News & Analysis API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # your React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
#live news
@app.get("/news", response_model=APIResponse)
def get_news():
    """
    Fetch and categorize latest market news.
    Refreshes every time the browser refreshes.
    """
    # --- FIX 1: Import locally to avoid circular dependency ---
    from services.news_categorizer import categorize_news
    
    articles = fetch_news()
    categorized = categorize_news(articles)
    return APIResponse(section="Latest Market News & Analysis", items=categorized)

#ai market insights
@app.get("/market-insights", response_model=MarketInsights)
async def get_insights():
    """
    Endpoint to get AI-generated market insights.
    This endpoint calls the async service function to get the data.
    """
    # --- FIX 2: Import locally to avoid circular dependency ---
    from services.market_insights import get_market_insights_async
    
    try:
        # Await the imported async function
        insights = await get_market_insights_async()
        if not insights:
            raise HTTPException(status_code=404, detail="No insights could be generated.")
        return insights
    except Exception as e:
        # Handle exceptions that might occur during the async operation
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

#graphs
@app.get("/live-indices")
def get_live_indices():
    """
    API wrapper around fetch_live_indices function
    """
    indices = fetch_live_indices()
    if not indices:
        raise HTTPException(status_code=500, detail="Failed to fetch index data.")
    return indices

@app.post("/chat", response_model=ChatResponse)
@app.post("/chat/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for finance queries using the new stock assistant pipeline."""
    return await process_stock_query_fast(request.query)

#watchlist 
@app.get("/api/stock/{company}")
def get_stock(company: str):
    try:
        # Find ticker automatically
        ticker = get_ticker_from_company(company)
        stock = yf.Ticker(ticker)

        info = stock.info
        return {
            "ticker": ticker,
            "name": info.get("longName", company),
            "price": info.get("currentPrice"),
            "change": info.get("regularMarketChangePercent", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
 
@app.get("/sentiment")
async def sentiment(query: str = Query(..., description="Company name or ticker")):
    return await analyze_sentiment(query)

# #balance sheet analyzer
@app.post("/parse-bank-statement")
async def parse_bank_statement(file: UploadFile = File(...)):
    """
    Upload a bank statement PDF, extract JSON,
    and store transactions in the database.
    """

    # Save uploaded file temporarily
    temp_pdf_path = f"/tmp/{file.filename}"
    with open(temp_pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse the bank statement
    parser = BankStatementParser(temp_pdf_path)
    transactions = parser.to_json()  # <-- list of dicts

    # Save to database
    save_transactions(transactions)

    return JSONResponse(content={
        "message": "Parsed and stored successfully.",
        "transactions_stored": len(transactions),
        "data": transactions
    })
    
DB_PATH = os.getenv("BANK_DB_PATH", "backend/bank_statements.db")

@app.get("/health")
def health():
    return {"status": "ok", "db_path": DB_PATH}

@app.get("/analytics")
def analytics(use_llm: Optional[bool] = Query(True, description="Whether to use LLM fallback for uncategorized merchants")):
    # read transactions
    txs = read_transactions_from_db(DB_PATH)
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found in DB")

    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    summary = monthly_spend_summary(categorized)

    # include a small sample of categorized transactions
    sample = categorized[:20]

    return JSONResponse(content={
        "summary": summary,
        "sample_transactions": sample,
        "counts": {
            "total_transactions": len(categorized),
            "llm_classified": sum(1 for t in categorized if t.get("llm_used"))
        }
    })

@app.get("/chart/category_pie.png")
def category_pie(use_llm: Optional[bool] = Query(True)):
    txs = read_transactions_from_db(DB_PATH)
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found in DB")
    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    summary = monthly_spend_summary(categorized)
    img_bytes = pie_chart_category(summary["amount_per_category"])
    return Response(content=img_bytes, media_type="image/png")

@app.get("/chart/top_merchants.png")
def top_merchants_chart(use_llm: Optional[bool] = Query(True), top_n: Optional[int] = Query(5)):
    txs = read_transactions_from_db(DB_PATH)
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found in DB")
    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    img_bytes = bar_chart_top_merchants(categorized, top_n=top_n)
    return Response(content=img_bytes, media_type="image/png")

@app.get("/analytics/embedded")
def analytics_embedded(use_llm: Optional[bool] = Query(True)):
    """
    Returns JSON summary + base64-encoded PNG images for easy embedding in clients.
    """
    txs = read_transactions_from_db(DB_PATH)
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found in DB")
    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    summary = monthly_spend_summary(categorized)

    pie_png = pie_chart_category(summary["amount_per_category"])
    bar_png = bar_chart_top_merchants(categorized)

    return {
        "summary": summary,
        "pie_png_base64": base64.b64encode(pie_png).decode(),
        "bar_png_base64": base64.b64encode(bar_png).decode(),
    }

#stock screener dynamic sector stocks
@app.post("/get-sector-stocks")
# To avoid blocking the event loop with synchronous yfinance/LLM calls, 
# you should ideally run this in a separate thread pool using 
# `await asyncio.to_thread(scraper.get_stocks)` or `run_in_threadpool`.
# For simplicity and direct relevance to your class, this is the synchronous route:
def get_sector_stocks_sync(req: SectorRequest):
    """
    1. Instantiates DynamicSectorStockScraper with the user-provided sector.
    2. Uses LLM to find Indian companies and convert them to NSE tickers.
    3. Fetches stock data using yfinance.
    4. Returns the structured results.
    """
    try:
        scraper = DynamicSectorStockScraper(sector=req.sector)
        results = scraper.get_stocks()
        return results
    except Exception as e:
        return {
            "status": "error",
            "message": f"An unexpected error occurred: {str(e)}"
        }
