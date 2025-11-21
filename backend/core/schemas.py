from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass
from pydantic import BaseModel, Field

# -------------------------------------------------------------------
# 1. News & Categorization Schemas
# -------------------------------------------------------------------

class NewsArticle(BaseModel):
    title: str
    excerpt: Optional[str] = None 
    source: str
    published_at: str

class CategorizedNews(BaseModel):
    category: str
    title: str
    excerpt: str
    source: str
    published_at: str

class APIResponse(BaseModel):
    section: str
    items: List[CategorizedNews]

# -------------------------------------------------------------------
# 2. Market Insights (AI Analysis)
# -------------------------------------------------------------------

class MarketInsights(BaseModel):
    market_sentiment: str = Field(..., description="Overall market sentiment, e.g., 'Bullish', 'Neutral', 'Bearish'.")
    market_sentiment_description: str = Field(..., description="A two-line summary explaining the market sentiment.")
    
    volatility_alert: str = Field(..., description="Expected market volatility, e.g., 'High', 'Moderate', 'Low'.")
    volatility_alert_description: str = Field(..., description="Explanation of expected price swings.")
    
    top_recommendation: str = Field(..., description="Key recommendation for a sector/stock with an emoji.")
    # --- CRITICAL FIX: Added this missing field below ---
    top_recommendation_description: str = Field(..., description="Summary of the recommendation upside.")
    
    risk_assessment: str = Field(..., description="Overall risk level, e.g., 'High', 'Medium', 'Low'.")
    risk_assessment_description: str = Field(..., description="Justification for the risk assessment.")

# -------------------------------------------------------------------
# 3. Chatbot Schemas
# -------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str = Field(..., description="User's finance-related query")

class StockData(BaseModel):
    ticker: Optional[str] = None
    company_name: Optional[str] = None
    current_price: Optional[float] = None
    previous_close: Optional[float] = None
    market_cap: Optional[float] = None
    currency: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    price_change: Optional[float] = None
    price_change_percent: Optional[float] = None

class ChatResponse(BaseModel):
    answer: str
    stock_data: Optional[StockData] = None
    raw_data: Optional[Dict[str, Any]] = None
    query_type: str = Field(default="general", description="Type of query: stock, general, error")

# -------------------------------------------------------------------
# 4. Charting & Indices
# -------------------------------------------------------------------

class ChartDataPoint(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: int

class IndexChart(BaseModel):
    symbol: str
    name: str
    data: List[ChartDataPoint]

class IndexList(BaseModel):
    indices: List[IndexChart]

# -------------------------------------------------------------------
# 5. Sentiment Analysis (Specific Engine)
# -------------------------------------------------------------------

class SentimentRequest(BaseModel):
    query: str = Field(..., description="Stock ticker or company name.")
    max_articles: int = Field(10, ge=1, le=50)
    analyzer: Optional[str] = Field("rule")

class ArticleSentiment(BaseModel):
    title: str
    link: Optional[str] = None
    published: Optional[datetime] = None
    snippet: Optional[str] = None
    score: float
    label: str

class AggregatedSentiment(BaseModel):
    query: str
    analyzed_articles: int
    average_score: float
    overall_label: str
    per_article: List[ArticleSentiment]

class StockRequest(BaseModel):
    stock_ticker: str 

class TrendingTicker(BaseModel):
    ticker: str
    sentiment_score: float
    trend_percentage: float

class MarketPrediction(BaseModel):
    message: str

class StockResponse(BaseModel):
    stock_ticker: str
    sentiment_score: float
    trending_tickers: List[TrendingTicker]
    market_prediction: MarketPrediction
    timestamp: datetime

# -------------------------------------------------------------------
# 6. Balance Sheet / Transactions
# -------------------------------------------------------------------

@dataclass
class Transaction:
    date: str           
    time: Optional[str] 
    transaction_type: str  
    name: str           
    amount: float       

    def normalized_datetime(self) -> datetime:
        """
        Parses date string into a datetime object.
        """
        date_str = self.date.strip()
        # Try specific formats first
        formats = [
            "%d %b, %Y %I:%M %p", # 12 Nov, 2024 01:24 PM
            "%d %b, %Y",          # 12 Nov, 2024
            "%Y-%m-%d %H:%M:%S",  
            "%Y-%m-%d"
        ]
        
        for fmt in formats:
            try:
                if "%I:%M %p" in fmt and self.time:
                    return datetime.strptime(f"{date_str} {self.time}", fmt)
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Fallback
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
            return datetime.now()