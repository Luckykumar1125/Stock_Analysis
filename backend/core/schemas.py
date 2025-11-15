from __future__ import annotations
from pydantic import BaseModel,Field,validator
from typing import List,Optional,Dict,Any
from datetime import date,datetime
from enum import Enum
from sqlmodel import SQLModel, Field as ORMField
import os
import json
import datetime as dt


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

class MarketInsights(BaseModel):
    market_sentiment: str = Field(..., description="Overall market sentiment, e.g., 'Bullish', 'Neutral', 'Bearish'.")
    market_sentiment_description: str = Field( ..., description="A two-line summary explaining the market sentiment based on news.")
    volatility_alert: str = Field(..., description="Expected market volatility, e.g., 'High', 'Moderate', 'Low'.")
    volatility_alert_description: str = Field(..., description="A two-line explanation of the expected price swings and the reasons.")
    top_recommendation: str = Field(..., description="A key recommendation for a sector or stock based on the analysis.")
    risk_assessment: str = Field(..., description="Overall risk level for current market conditions, e.g., 'High', 'Medium', 'Low'.")
    risk_assessment_description: str = Field(..., description="A two-line justification for the risk assessment, referencing market conditions."
    )


class APIResponse(BaseModel):
    section: str
    items: List[CategorizedNews]

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


#sentiment
class SentimentRequest(BaseModel):
    query: str = Field(..., description="Stock ticker or company name to search news for, e.g. AAPL or Apple Inc.")
    max_articles: int = Field(10, ge=1, le=50, description="Max number of articles to fetch and analyze")
    analyzer: Optional[str] = Field("rule", description="Analyzer to use: 'rule' or 'hf'")

class ArticleSentiment(BaseModel):
    title: str
    link: Optional[str] = None
    published: Optional[datetime] = None
    snippet: Optional[str] = None
    score: float = Field(..., description="Sentiment score; positive >0, negative <0, range roughly -1..1")
    label: str = Field(..., description="'POSITIVE', 'NEGATIVE', or 'NEUTRAL'")

class AggregatedSentiment(BaseModel):
    query: str
    analyzed_articles: int
    average_score: float
    overall_label: str
    per_article: List[ArticleSentiment]

#balance sheet
class ChunkMetadata(BaseModel):
    section: Optional[str]
    heading_level: Optional[int]
    source_file: Optional[str]
    position: Optional[int]


class TextChunk(BaseModel):
    text: str
    metadata: ChunkMetadata


class BalanceSheetItem(BaseModel):
    category: str
    amount: float
    type: str


class BalanceSheetRatios(BaseModel):
    current_ratio: float
    debt_to_equity: float
    equity_ratio: float


class BalanceSheetResponse(BaseModel):
    items: List[BalanceSheetItem]
    ratios: BalanceSheetRatios
    explanation: str
    chunks: Optional[List[TextChunk]] = Field(default=None, description="Chunked text with metadata")


