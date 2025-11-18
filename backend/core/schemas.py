from __future__ import annotations
from pydantic import BaseModel,Field,validator
from typing import List,Optional,Dict,Any
from datetime import date,datetime
from enum import Enum
from sqlmodel import SQLModel, Field as ORMField
import os
import json
import datetime as dt
from pydantic import BaseModel, Field, field_validator


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
class TransactionType(str, Enum):
    """Transaction type enum"""
    PAID = "paid"
    RECEIVED = "received"
    SELF_TRANSFER = "self_transfer"


class Transaction(BaseModel):
    """Individual transaction model"""
    date: str = Field(..., description="Transaction date")
    time: str = Field(..., description="Transaction time")
    transaction_type: TransactionType = Field(..., description="Type of transaction")
    counterparty: str = Field(..., description="Person or merchant involved")
    upi_transaction_id: str = Field(..., description="UPI transaction ID")
    bank_account: str = Field(..., description="Bank account used")
    amount: float = Field(..., gt=0, description="Transaction amount")
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return round(v, 2)
    
    @field_validator('counterparty')
    @classmethod
    def clean_counterparty(cls, v):
        return v.strip()


class StatementSummary(BaseModel):
    """Statement summary model"""
    period_start: str = Field(..., description="Statement period start date")
    period_end: str = Field(..., description="Statement period end date")
    total_sent: float = Field(..., ge=0, description="Total amount sent")
    total_received: float = Field(..., ge=0, description="Total amount received")
    account_number: str = Field(..., description="Account number")
    email: str = Field(..., description="Email associated with account")
    
    @field_validator('total_sent', 'total_received')
    @classmethod
    def round_amount(cls, v):
        return round(v, 2)


class GPAYStatement(BaseModel):
    """Complete GPAY statement model"""
    summary: StatementSummary
    transactions: List[Transaction] = Field(default_factory=list)
    
    @property
    def transaction_count(self) -> int:
        """Get total number of transactions"""
        return len(self.transactions)
    
    @property
    def paid_transactions(self) -> List[Transaction]:
        """Get all paid transactions"""
        return [t for t in self.transactions if t.transaction_type == TransactionType.PAID]
    
    @property
    def received_transactions(self) -> List[Transaction]:
        """Get all received transactions"""
        return [t for t in self.transactions if t.transaction_type == TransactionType.RECEIVED]
    
    @property
    def self_transfer_transactions(self) -> List[Transaction]:
        """Get all self transfer transactions"""
        return [t for t in self.transactions if t.transaction_type == TransactionType.SELF_TRANSFER]
    
    def to_json(self, filepath: str):
        """Save statement to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, filepath: str):
        """Load statement from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)
    
    def get_transactions_by_counterparty(self, counterparty: str) -> List[Transaction]:
        """Get all transactions with a specific counterparty"""
        return [t for t in self.transactions if counterparty.lower() in t.counterparty.lower()]
    
    def get_transactions_by_date(self, date: str) -> List[Transaction]:
        """Get all transactions on a specific date"""
        return [t for t in self.transactions if t.date == date]