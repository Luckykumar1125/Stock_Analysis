import os
import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Optional
from datetime import date, timedelta
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Depends, Body
from pydantic import BaseModel, Field, validator
from groq import Groq
from dotenv import load_dotenv

# Load environment variables (ensure GROQ_API_KEY is set in .env)
load_dotenv()

def safe_float(x):
    """Convert NaN/Inf to 0 for JSON safety."""
    if x is None:
        return 0
    if isinstance(x, float):
        if np.isnan(x) or np.isinf(x):
            return 0.0
    return x

from yahooquery import search

def resolve_to_yf_ticker(symbol: str) -> str:
    """
    Convert company names into Yahoo Finance-compatible tickers.
    Example: 'Tata Motors' → 'TATAMOTORS.NS'
    """
    symbol = symbol.strip()

    # If already a ticker (no spaces + contains .NS or .BO), return as is
    if " " not in symbol and (symbol.endswith(".NS") or symbol.endswith(".BO") or symbol.isupper()):
        return symbol.upper()

    # Search YahooQuery API
    try:
        result = search(symbol)
        quotes = result.get("quotes", [])

        for q in quotes:
            t = q.get("symbol", "")
            # Prefer Indian NSE tickers
            if t.endswith(".NS"):
                return t
            # fallback: anything valid
            if t:
                return t
    except:
        pass

    raise HTTPException(
        status_code=400,
        detail=f"Could not resolve '{symbol}' to a Yahoo Finance ticker."
    )

# --- 1. API DATA MODELS (Pydantic) ---

class StockPositionRequest(BaseModel):
    symbol: str = Field(..., min_length=1, to_upper=True, description="Ticker symbol (e.g., AAPL)")
    purchase_date: date = Field(..., description="Date of purchase (YYYY-MM-DD)")
    quantity: float = Field(..., gt=0, description="Number of shares held")
    purchase_price: Optional[float] = Field(None, gt=0, description="Cost basis per share. If null, tries to fetch historical price.")

    @validator('purchase_date')
    def date_must_be_past(cls, v):
        if v > date.today():
            raise ValueError('Purchase date cannot be in the future')
        return v

class PortfolioRequest(BaseModel):
    positions: List[StockPositionRequest]
    benchmark: str = Field("^GSPC", description="Benchmark ticker (default: S&P 500)")
    risk_free_rate: float = Field(0.04, description="Risk-free rate for Sharpe calculation (default: 4%)")

class HoldingMetric(BaseModel):
    symbol: str
    current_price: float
    total_gain_loss_pct: float
    cagr: float
    volatility_annualized: float
    beta: float
    sharpe_ratio: float
    weight_in_portfolio: float

class PortfolioAnalysisResult(BaseModel):
    total_value: float
    total_gain_loss_pct: float
    portfolio_volatility: float
    diversification_index: float
    holdings: List[HoldingMetric]

class PortfolioAPIResponse(BaseModel):
    analysis: PortfolioAnalysisResult
    ai_rebalancing_advice: str

# --- 2. SERVICE LAYER (Business Logic) ---

# --- 2. SERVICE LAYER (Business Logic) ---

class PortfolioAnalyzerService:
    def __init__(self, positions: List[StockPositionRequest], benchmark: str, rf_rate: float):
        self.positions = positions
        self.benchmark = benchmark
        self.rf_rate = rf_rate
        
        # FIX 1: Create a map to link User Input -> Yahoo Ticker
        # Example: {"Tata Motors": "TATAMOTORS.NS", "AAPL": "AAPL"}
        self.symbol_map = {p.symbol: resolve_to_yf_ticker(p.symbol) for p in positions}
        
        # We only download the resolved tickers
        self.tickers = list(set(self.symbol_map.values()))
        self.start_date = min(p.purchase_date for p in positions)

    def _fetch_market_data(self):
        # Download all needed data in one batch for efficiency
        all_tickers = self.tickers + [self.benchmark]
        
        # FIX: add 1 day to today's date because yfinance 'end' parameter is EXCLUSIVE
        # If you use just date.today(), it cuts off the current day's data.
        end_date = date.today() + timedelta(days=1)

        data = yf.download(
            all_tickers, 
            start=self.start_date, 
            end=end_date,  # <--- UPDATED HERE
            progress=False,
            auto_adjust=False 
        )

        # Handle cases where yfinance returns MultiIndex columns (Price Type, Ticker)
        if isinstance(data.columns, pd.MultiIndex):
            try:
                data = data['Adj Close']
            except KeyError:
                data = data['Close']
        else:
            if 'Adj Close' in data.columns:
                data = data['Adj Close']
            elif 'Close' in data.columns:
                data = data['Close']
        
        return data

    def analyze(self) -> PortfolioAnalysisResult:
        if not self.positions:
            raise HTTPException(status_code=400, detail="No positions provided")

        try:
            full_data = self._fetch_market_data()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch market data: {str(e)}")

        # Ensure we have data
        if full_data.empty:
             raise HTTPException(status_code=400, detail="Market data download returned empty results.")

        # Separate stock data from benchmark
        # Handle case where benchmark might be missing from columns
        if self.benchmark in full_data.columns:
            market_data = full_data[self.benchmark]
        elif self.benchmark in full_data.index: # unlikely but possible in Series
             market_data = full_data
        else:
             # Fallback: if benchmark download failed, use a proxy or zero returns (risky but prevents crash)
             market_data = pd.Series(index=full_data.index, data=100.0) 

        # Filter stock data (exclude benchmark from stock columns)
        # We verify which of our resolved tickers are actually in the dataframe
        available_tickers = [t for t in self.tickers if t in full_data.columns]
        if not available_tickers:
             raise HTTPException(status_code=400, detail="No stock data found for the provided symbols.")
             
        stock_data = full_data[available_tickers]

        # Handle single stock case (Only convert if it is actually a Series)
        if isinstance(stock_data, pd.Series):
            stock_data = stock_data.to_frame(name=available_tickers[0])

        # Calculate Returns
        stock_returns = stock_data.pct_change(fill_method=None).dropna()
        market_returns = market_data.pct_change(fill_method=None).dropna()
        
        # Align Indices
        common_dates = stock_returns.index.intersection(market_returns.index)
        stock_returns = stock_returns.loc[common_dates]
        market_returns = market_returns.loc[common_dates]

        holdings_metrics = []
        total_current_value = 0.0
        temp_holdings = []

        # 1. Calculate Values and Weights
        for p in self.positions:
            # FIX 2: Use the resolved ticker to look up data, not the user input
            resolved_ticker = self.symbol_map.get(p.symbol)
            
            if resolved_ticker not in stock_data.columns:
                print(f"Warning: {resolved_ticker} data missing.")
                continue
            
            try:
                # Get latest price
                curr_price = float(stock_data[resolved_ticker].iloc[-1])
                
                # Clean dirty data (NaN/Inf)
                if np.isnan(curr_price) or np.isinf(curr_price):
                    continue

                val = curr_price * p.quantity
                total_current_value += val
                
                # Determine buy price
                buy_price = p.purchase_price
                if buy_price is None:
                    try:
                        buy_price = float(stock_data[resolved_ticker].asof(pd.to_datetime(p.purchase_date)))
                    except:
                        buy_price = curr_price 

                temp_holdings.append({
                    "pos": p,
                    "ticker": resolved_ticker, # Store resolved ticker for next loop
                    "val": val,
                    "curr_price": curr_price,
                    "buy_price": buy_price
                })
            except IndexError:
                continue

        if total_current_value == 0:
            raise HTTPException(status_code=400, detail="Total portfolio value is zero. Check if symbols are valid (e.g. 'RELIANCE.NS').")

        # 2. Calculate Risk Metrics
        for item in temp_holdings:
            p = item['pos']
            ticker = item['ticker'] # Use resolved ticker
            
            # Handle cases where returns might be missing for this specific stock (e.g. recently listed)
            if ticker not in stock_returns.columns:
                vol, beta, sharpe = 0.0, 0.0, 0.0
            else:
                s_rets = stock_returns[ticker]
                
                # Volatility
                vol = s_rets.std() * np.sqrt(252)
                
                # Beta
                try:
                    cov = np.cov(s_rets, market_returns)[0][1]
                    m_var = np.var(market_returns)
                    beta = cov / m_var if m_var > 0 else 0
                except:
                    beta = 1.0 # Default fallback
                
                # Sharpe
                excess_ret = s_rets.mean() * 252 - self.rf_rate
                sharpe = excess_ret / vol if vol > 0 else 0
            
            # Gains
            buy_price = item['buy_price'] if item['buy_price'] > 0 else item['curr_price']
            total_gain = (item['curr_price'] - buy_price) / buy_price
            
            days = (date.today() - p.purchase_date).days
            years = days / 365.25
            
            if years > 0 and item['curr_price'] > 0 and buy_price > 0:
                cagr = ((item['curr_price'] / buy_price) ** (1/years) - 1)
            else:
                cagr = 0.0
            
            weight = item['val'] / total_current_value
            
            holdings_metrics.append(HoldingMetric(
                symbol=ticker,
                current_price=safe_float(round(item['curr_price'], 2)),
                total_gain_loss_pct=safe_float(round(total_gain * 100, 2)),
                cagr=safe_float(round(cagr * 100, 2)),
                volatility_annualized=safe_float(round(vol, 3)),
                beta=safe_float(round(beta, 2)),
                sharpe_ratio=safe_float(round(sharpe, 2)),
                weight_in_portfolio=safe_float(round(weight, 4))
            ))

        # 3. Portfolio Level Aggregations
        weights_arr = np.array([h.weight_in_portfolio for h in holdings_metrics])
        
        if len(holdings_metrics) > 0:
            # Filter columns to match holdings
            active_tickers = [h.symbol for h in holdings_metrics]
            
            # Calculate Portfolio Volatility
            try:
                cov_matrix = stock_returns[active_tickers].cov() * 252
                port_var = np.dot(weights_arr.T, np.dot(cov_matrix, weights_arr))
                port_vol = np.sqrt(port_var)
            except:
                port_vol = 0.0
            
            # Calculate Diversification Index
            try:
                corr_matrix = stock_returns[active_tickers].corr()
                np.fill_diagonal(corr_matrix.values, np.nan)
                if corr_matrix.isna().all().all() or len(holdings_metrics) <= 1:
                    avg_corr = 1.0 
                else:
                    avg_corr = np.nanmean(corr_matrix.values)
                div_index = 1.0 - avg_corr
            except:
                div_index = 0.0
        else:
            port_vol = 0.0
            div_index = 0.0
            
        total_gain_loss = sum([h.total_gain_loss_pct * h.weight_in_portfolio for h in holdings_metrics])

        return PortfolioAnalysisResult(
            total_value=round(total_current_value, 2),
            total_gain_loss_pct=round(total_gain_loss, 2),
            portfolio_volatility=round(port_vol, 3),
            diversification_index=round(div_index, 2),
            holdings=holdings_metrics
        )

# --- 3. DEPENDENCY INJECTION (AI Advisor) ---

@lru_cache()
def get_groq_client():
    """Singleton dependency for Groq client to avoid overhead."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured on server.")
    return Groq(api_key=api_key)

def generate_advice(analysis: PortfolioAnalysisResult, client: Groq) -> str:
    system_prompt = """
    You are a sophisticated Financial Portfolio Manager. 
    Analyze the JSON data provided.
    1. Assess the Portfolio Volatility and Beta.
    2. Evaluate the Diversification Index (closer to 1 is better).
    3. Provide 3 bullet points on specific rebalancing actions.
    """
    
    try:
        chat = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": analysis.model_dump_json()}
            ],
            # FIX: Use a currently active model alias
            model="llama-3.3-70b-versatile", 
            temperature=0.5,
        )
        return chat.choices[0].message.content
    except Exception as e:
        # This ensures the API doesn't crash if AI fails, but returns the error message
        return f"AI Advice unavailable: {str(e)}"