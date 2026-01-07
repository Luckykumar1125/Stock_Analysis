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
from storage.db import save_transactions,get_session
import uuid
import shutil,datetime,tempfile
from services.balance_sheet_analyzer.processor_llm import (
    read_transactions_from_db,
    categorize_transactions,
    monthly_spend_summary,
    pie_chart_category,
    bar_chart_top_merchants,
    generate_spending_insights
)
from services.news_categorizer import categorize_news
import os,requests,re,logging
import base64
from typing import Optional,Dict, Any
from services.stock_screener.dynamic_scrapper import DynamicSectorStockScraper
from pydantic import BaseModel,HttpUrl
# from services.sentiment_analysis.engine import (
#     fetch_news_for_ticker,
#     fetch_reddit_mentions,
#     fetch_twitter_mentions,
#     analyze_sentiment_with_llm,
#     fetch_stock_price
# )
# from core.schemas import StockRequest, StockResponse, MarketPrediction, TrendingTicker
# from services.sentiment_analysis.engine import generate_market_prediction, identify_trending_tickers
from services.upcoming_sales import scrape_upcoming_sales, SalesResponse
from services.portfolio_analyzer.portfolio import PortfolioAnalyzerService,generate_advice,PortfolioRequest,get_groq_client,Groq,PortfolioAPIResponse
from services.price_prediction.price import predict_stock_price, StockRequest
CURRENT_DB_PATH = None
router = APIRouter()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
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
    # 1. Fetch raw articles
    # Note: This takes time (API calls). Be aware this makes the endpoint slow.
    articles = fetch_news()
    
    # 2. Process with LLM
    # Note: This takes even more time (LLM generation).
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
    global CURRENT_DB_PATH  # <--- Allow modifying the global variable

    # 1. Get the correct temporary directory for the OS (Windows/Mac/Linux)
    temp_dir = tempfile.gettempdir()

    # 2. Construct the safe PDF path
    temp_pdf_path = os.path.join(temp_dir, file.filename)
    
    # Save uploaded file temporarily
    with open(temp_pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse the bank statement
    parser = BankStatementParser(temp_pdf_path)
    transactions = parser.to_json() 

    # 3. Construct the safe Database path
    temp_db_path = os.path.join(temp_dir, f"bank_{uuid.uuid4().hex}.db")
    
    # Save to database
    session = get_session(temp_db_path)
    save_transactions(transactions, session)

    # Update the global variable
    CURRENT_DB_PATH = temp_db_path 

    return {
        "message": "Parsed and stored successfully.",
        "transactions_stored": len(transactions),
        "db_path": temp_db_path,          
        "data": transactions
    }

@app.get("/analytics")
def analytics(
    db_path: str = Query(...),
    use_llm: bool = Query(True)
):
    # Use the db_path provided in the Query, not the global one
    if not db_path or not os.path.exists(db_path):
        raise HTTPException(status_code=400, detail="Database file not found.")

    txs = read_transactions_from_db(db_path)

    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found")

    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    summary = monthly_spend_summary(categorized)

    return {
        "summary": summary,
        "sample_transactions": categorized[:20],
        "counts": {
            "total_transactions": len(categorized),
            "llm_classified": sum(1 for t in categorized if t.get("llm_used"))
        }
    }

@app.get("/chart/category_pie.png")
def category_pie(
    db_path: str = Query(...),
    use_llm: bool = True
):
    txs = read_transactions_from_db(db_path)
    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    summary = monthly_spend_summary(categorized)
    img_bytes = pie_chart_category(summary["amount_per_category"])
    return Response(content=img_bytes, media_type="image/png")


@app.get("/chart/top_merchants.png")
def top_merchants_chart(
    db_path: str = Query(...),
    use_llm: bool = True,
    top_n: int = 5
):
    txs = read_transactions_from_db(db_path)
    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    img_bytes = bar_chart_top_merchants(categorized, top_n=top_n)
    return Response(content=img_bytes, media_type="image/png")


@app.get("/analytics/embedded")
def analytics_embedded(use_llm: Optional[bool] = Query(True)):
    global CURRENT_DB_PATH

    if not CURRENT_DB_PATH:
        raise HTTPException(status_code=400, detail="No bank statement uploaded yet.")

    txs = read_transactions_from_db(CURRENT_DB_PATH)
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
        "db_used": CURRENT_DB_PATH
    }

@app.get("/analytics/ai-insights")
def get_ai_spending_insights(use_llm: bool = True):
    """
    Returns AI-generated advice on where to cut costs and how to save
    based on the currently uploaded bank statement.
    """
    global CURRENT_DB_PATH

    if not CURRENT_DB_PATH:
        raise HTTPException(status_code=400, detail="No bank statement uploaded yet.")

    # 1. Load Data
    txs = read_transactions_from_db(CURRENT_DB_PATH)
    if not txs:
        raise HTTPException(status_code=404, detail="No transactions found")

    # 2. Process Data
    categorized = categorize_transactions(txs, use_llm_fallback=use_llm)
    summary = monthly_spend_summary(categorized)

    # 3. Generate Insights using LLM
    insights = generate_spending_insights(summary)

    return {
        "financial_health": {
            "income": summary["total_received"],
            "expense": summary["total_spent"],
            "savings_rate": round((summary["net_savings"] / summary["total_received"] * 100), 1) if summary["total_received"] > 0 else 0
        },
        "ai_advice": insights
    }
    
    
#stock screener dynamic sector stocks
@app.post("/get-sector-stocks")
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

#sentiment analysis
# @app.post("/analyze_stock", response_model=StockResponse)
# def analyze_stock(request: StockRequest):
#     ticker = request.stock_ticker.upper()

#     # Fetch data
#     news = fetch_news_for_ticker(ticker)
#     reddit_posts = fetch_reddit_mentions(ticker)
#     tweets = fetch_twitter_mentions(ticker)

#     if not (news or reddit_posts or tweets):
#         raise HTTPException(status_code=404, detail="No data found for that ticker")

#     combined_texts = news + reddit_posts + tweets

#     # Sentiment
#     sentiment_score = analyze_sentiment_with_llm(combined_texts)

#     # Trending tickers
#     trending = identify_trending_tickers(combined_texts)

#     # Stock price
#     price = fetch_stock_price(ticker)

#     # Prediction
#     prediction = generate_market_prediction(ticker, sentiment_score, price)

#     return StockResponse(
#         stock_ticker=ticker,
#         sentiment_score=sentiment_score,
#         trending_tickers=trending,
#         market_prediction=prediction,
#         timestamp=datetime.utcnow(),
#     )

#upcoming sales scraper
@app.get("/api/upcoming-sales", response_model=SalesResponse)
def get_upcoming_sales():
    """
    Triggers a live web scrape to find the latest upcoming sales.
    Warning: This endpoint takes 5-10 seconds to execute.
    """
    try:
        data = scrape_upcoming_sales()
        
        if not data.sales:
            # If search failed, return empty list but 200 OK
            return {
                "sales": [],
                "last_updated": "Now (No sales found)"
            }
            
        return data
        
    except Exception as e:
        print(f"Scraper Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sales data")
    
    
#portfolio_analyzer endpoints would go here
@app.post("/analyze", response_model=PortfolioAPIResponse)
def analyze_portfolio(
    request: PortfolioRequest,
    client: Groq = Depends(get_groq_client)
):
    """
    Analyzes a stock portfolio and returns risk metrics + AI advice.
    """
    # 1. Run Financial Math
    analyzer = PortfolioAnalyzerService(request.positions, request.benchmark, request.risk_free_rate)
    analysis_result = analyzer.analyze()
    
    # 2. Get AI Advice
    ai_advice = generate_advice(analysis_result, client)
    
    # 3. Return Composite Response
    return PortfolioAPIResponse(
        analysis=analysis_result,
        ai_rebalancing_advice=ai_advice
    )
    
    
#price prediction
@app.post("/api/predict-stock")
async def api_predict_stock(req: StockRequest):
    # req.ticker can now be "Reliance", "Zomato", etc.
    result = predict_stock_price(req.ticker, req.days_ahead)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Could not find stock data for '{req.ticker}'")
    
    base64_img = base64.b64encode(result["image_bytes"]).decode('utf-8')
    
    return {
        "ticker": result["summary"]["ticker"],     # Return the ACTUAL ticker found
        "company_name": result["summary"]["company_name"], # Return the full name
        "image_base64": base64_img,
        "forecast_values": result["forecast_values"],
        "summary": result["summary"]
    }