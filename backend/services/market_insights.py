import os
import requests
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from core.schemas import MarketInsights

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
NEWS_API_URL_INSIGHTS = os.getenv("NEWS_API_URL_INSIGHTS")

# Initialize LLM and chains once
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0,
    groq_api_key=GROQ_API_KEY
)

prompt = ChatPromptTemplate.from_messages(
    [
         ("system",
         "You are a specialized market analyst AI. Your task is to provide a structured market report based on the provided news articles. "
         "You must strictly adhere to the following rules:"
         "1. Analyze the overall market sentiment and provide a clear label (`market_sentiment`)."
         "2. Write a brief, two-line description for the sentiment (`market_sentiment_description`), explaining why it was chosen."
         "3. Assess market volatility and provide a clear label (`volatility_alert`)."
         "4. Write a two-line explanation for the volatility (`volatility_alert_description`), including a price swing range (e.g., '2-3%')."
         "5. Identify the top investment recommendation and provide a label (`top_recommendation`), including a relevant emoji."
         "6. Write a two-line summary of the recommendation (`top_recommendation_description`), referencing the upside potential."
         "7. Evaluate the overall risk and provide a label (`risk_assessment`)."
         "8. Write a two-line justification for the risk assessment (`risk_assessment_description`), referencing current market conditions."
         "9. The final output must be a single, valid JSON object that conforms exactly to the provided schema, with no additional text or conversational phrases. All insights must be directly inferred from the news context."),
        ("human", "Analyze the following news articles to create a market report:\n\n{news_text}")
    ]
)

analysis_chain = prompt | llm.with_structured_output(schema=MarketInsights)

def fetch_news_sync(query: str) -> str:
    """A synchronous helper function to fetch news."""
    try:
        params = {
            'q': query,
            'apiKey': NEWS_API_KEY,
            'language': 'en',
            'sortBy': 'relevancy',
            'pageSize': 10
        }
        response = requests.get(NEWS_API_URL_INSIGHTS, params=params)
        response.raise_for_status()
        articles = response.json().get('articles', [])
        
        return "\n\n".join([
            f"Title: {article.get('title', '')}\nDescription: {article.get('description', '')}"
            for article in articles
        ])
    except Exception as e:
        print(f"Error fetching news: {e}")
        return ""

async def get_market_insights_async() -> MarketInsights:
    """
    An async function that orchestrates the data fetching and analysis.
    This is the function you will import.
    """
    # Note: requests is a synchronous library.
    # FastAPI automatically runs sync functions in a threadpool to avoid blocking.
    # So you don't need to manually use run_in_executor here.
    news_data = fetch_news_sync(query="AI innovation, tech stocks, market trends")
    
    if not news_data:
        # Return a default model instance on failure
        return MarketInsights(
            market_sentiment="Neutral",
            volatility_alert="Low",
            top_recommendation="No data available",
            risk_assessment="Low"
        )
    
    # Invoke the LangChain for structured extraction
    insights = analysis_chain.invoke({"news_text": news_data})
    
    return insights