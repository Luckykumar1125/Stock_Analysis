import os
from typing import Optional, Dict, Any
import yfinance as yf
from yahooquery import search
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from core.schemas import ChatResponse, StockData
from fastapi import HTTPException
import re

try:
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY environment variable not set.")

    llm = ChatGroq(
        temperature=0.3,
        model_name="meta-llama/llama-4-maverick-17b-128e-instruct",
        groq_api_key=GROQ_API_KEY
    )
except Exception as e:
    print(f"Error initializing Groq LLM: {e}")
    llm = None


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

STOCK_INSIGHT_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
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
    ),
    ("human", "User Query: {user_query}\n\nStock Data: {stock_data}")
])


GENERAL_FINANCE_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """
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
    ),
    ("human", "User Query: {user_query}")
])



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


async def process_chat_query(query: str) -> ChatResponse:
    """Main function to process user queries about finance"""
    
    if not llm:
        raise HTTPException(status_code=503, detail="Chatbot service not available. Check GROQ_API_KEY.")
    
    try:
        # Classify the query type
        query_type = classify_query(query)
        
        if query_type == "stock":
            return await process_stock_query(query)
        else:
            return await process_general_finance_query(query)
            
    except Exception as e:
        return ChatResponse(
            answer=f"I apologize, but I encountered an error processing your query: {str(e)}. Please try again or rephrase your question.",
            query_type="error"
        )

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



async def process_stock_query(query: str) -> ChatResponse:
    """Process stock-specific queries"""
    
    # Step 1: Resolve ticker
    ticker = resolve_query_to_ticker(query)
    
    if not ticker:
        # If no ticker found, try general finance response
        return await process_general_finance_query(query)
    
    # Step 2: Fetch stock data
    stock_data = fetch_stock_info(ticker)
    
    if not stock_data:
        return ChatResponse(
            answer=f"I found a ticker '{ticker}' but couldn't retrieve current data. This might be due to market hours or data availability. Would you like me to help you with general investment information instead?",
            query_type="stock"
        )
    
    # Step 3: Generate LLM insights
    try:
        response = llm.invoke(STOCK_INSIGHT_PROMPT.format(
            user_query=query,
            stock_data=stock_data
        ))
        
        response_text = response.content if hasattr(response, 'content') else str(response)
        formatted_answer = format_stock_response_to_bullets(response_text)

        return ChatResponse(
            answer=formatted_answer,
            stock_data=StockData(**stock_data),
            raw_data=stock_data,
            query_type="stock"
        )

    except Exception as e:
        return ChatResponse(
            answer=f"I found information about {stock_data.get('company_name', ticker)} but had trouble generating insights. Here's what I can tell you: Current price is ${stock_data.get('current_price', 'N/A')} in the {stock_data.get('sector', 'Unknown')} sector.",
            stock_data=StockData(**stock_data),
            raw_data=stock_data,
            query_type="stock"
        )


async def process_general_finance_query(query: str) -> ChatResponse:
    """Process general finance queries"""
    
    try:
        response = llm.invoke(GENERAL_FINANCE_PROMPT.format(user_query=query))
        answer_text = response.content if hasattr(response, 'content') else str(response)
        
        return ChatResponse(
            answer=answer_text,
            query_type="general"
        )
        
    except Exception as e:
        return ChatResponse(
            answer="I'd be happy to help you learn about finance! However, I'm having trouble generating a detailed response right now. Could you please be more specific about what you'd like to know? For example, are you interested in learning about stocks, mutual funds, how to start investing, or something else?",
            query_type="general"
        )
