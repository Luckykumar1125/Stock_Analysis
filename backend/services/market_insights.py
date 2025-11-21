import os
import httpx
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from core.schemas import MarketInsights

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL_INSIGHTS = os.getenv("NEWS_API_URL_INSIGHTS", "https://newsapi.org/v2/everything")

# --- 1. Initialize LLM ---
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2, # Slightly increased to allow for creative connection of facts
    groq_api_key=GROQ_API_KEY
)

# --- 2. Robust Prompt (Forces a Recommendation) ---
prompt = ChatPromptTemplate.from_messages(
    [
         ("system",
         """You are a Wall Street strategist. Generate a daily market report based on the news provided.

         CRITICAL INSTRUCTION FOR 'TOP RECOMMENDATION':
         - You MUST provide a recommendation. Do not leave it empty.
         - If the news mentions specific stocks (e.g., "Apple", "Tesla"), recommend the best one.
         - If NO specific stocks are mentioned, you MUST recommend a SECTOR based on sentiment (e.g., "Technology 💻", "Energy ⚡", "Defensive Stocks 🛡️").
         - Usage of emojis is highly encouraged for the visual appeal.
         
         Analyze the text below and populate the response strictly."""),
        ("human", "News Data:\n{news_text}")
    ]
)

# Bind the schema
analysis_chain = prompt | llm.with_structured_output(MarketInsights)

# --- 3. Tuned News Fetcher ---
async def fetch_news_async(query: str = "stock market") -> str:
    """Async helper to fetch HIGH QUALITY news."""
    async with httpx.AsyncClient() as client:
        try:
            params = {
                # We search for 'market', 'stocks', or 'trading' to ensure financial relevance
                'q': "stock market OR investing OR analyst ratings",
                'apiKey': NEWS_API_KEY,
                'language': 'en',
                # 'popularity' gives us major headlines (CNBC, Bloomberg) instead of random blogs
                'sortBy': 'popularity', 
                'pageSize': 8 
            }
            response = await client.get(NEWS_API_URL_INSIGHTS, params=params)
            response.raise_for_status()
            data = response.json()
            articles = data.get('articles', [])
            
            if not articles:
                return ""

            # improved formatting to help the AI understand the context
            news_text = "\n".join([
                f"- TITLE: {article.get('title', '')} | DESC: {article.get('description', '')}"
                for article in articles
                if article.get('title') and article.get('description') # Filter out empty trash
            ])
            return news_text
            
        except Exception as e:
            print(f"Error fetching news: {e}")
            return ""

# --- 4. Main Orchestrator ---
async def get_market_insights_async() -> MarketInsights:
    """
    Orchestrates fetching and analysis.
    """
    # 1. Fetch Data
    news_data = await fetch_news_async()
    
    # 2. Handle empty data (Fallback)
    if not news_data:
        return MarketInsights(
            market_sentiment="Neutral",
            market_sentiment_description="Data temporarily unavailable. Market appears stable.",
            volatility_alert="Low",
            volatility_alert_description="No significant news triggering volatility.",
            top_recommendation="Broad Market Index 📊",
            top_recommendation_description="Consider holding index funds until clearer signals emerge.",
            risk_assessment="Low",
            risk_assessment_description="Lack of data suggests no immediate high-impact threats."
        )
    
    # 3. Invoke LLM
    try:
        insights = await analysis_chain.ainvoke({"news_text": news_data})
        return insights
    except Exception as e:
        print(f"LLM Generation Error: {e}")
        # Fallback if LLM crashes
        return MarketInsights(
            market_sentiment="Neutral",
            market_sentiment_description="Analysis system is rebooting.",
            volatility_alert="Unknown",
            volatility_alert_description="Unable to calculate volatility.",
            top_recommendation="Cash 💵",
            top_recommendation_description="Stay in cash while we restore data feeds.",
            risk_assessment="Medium",
            risk_assessment_description="System error prevented full analysis."
        )