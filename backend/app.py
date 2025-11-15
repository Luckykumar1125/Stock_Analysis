from fastapi import FastAPI,WebSocket,APIRouter, Depends, HTTPException,Query,UploadFile
from core.schemas import APIResponse,MarketInsights,ChatRequest,ChatResponse
from services.news_fetcher import fetch_news
# from services.news_categorizer import categorize_news  <-- REMOVED FROM HERE
from fastapi.middleware.cors import CORSMiddleware
# from services.market_insights import get_market_insights_async <-- REMOVED FROM HERE
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from services.charts import fetch_live_indices
from services.finance import process_chat_query 
from services.watchlist import get_ticker_from_company
import yfinance as yf
from services.sentiment_analyzer import analyze_sentiment
from core.config import settings
import pandas as pd

from core.schemas import BalanceSheetResponse, BalanceSheetItem, BalanceSheetRatios

router = APIRouter()

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

#chatbot
@app.post("/chat", response_model=ChatResponse)
@app.post("/chat/", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Main chat endpoint for finance queries"""
    return await process_chat_query(request.query)

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
# @app.post("/analyze-balance-sheet", response_model=BalanceSheetResponse)
# async def analyze_balance_sheet(file: UploadFile):
#     """
#     Upload a company's balance sheet (PDF or CSV) and get categorized financial analysis.
#     Works for any company format.
#     """
#     try:
#         df = extract_balance_sheet(file)
#         df = categorize(df)
#         ratios = compute_ratios(df)
#         explanation = explain_ratios(ratios)

#         items = [BalanceSheetItem(category=row["Category"], amount=row["Amount"], type=row["Type"])
#                  for _, row in df.iterrows()]
#         ratio_model = BalanceSheetRatios(**ratios)

#         return BalanceSheetResponse(items=items, ratios=ratio_model, explanation=explanation)

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Error analyzing balance sheet: {str(e)}")