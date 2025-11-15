import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    NEWS_API_KEY: str
    GROQ_API_KEY: str
    MODEL_NAME: str = "meta-llama/llama-guard-4-12b"
    NEWS_API_URL: str = "https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize=20"
    NEWS_API_URL_INSIGHTS: str ="https://newsapi.org/v2/everything"
    WATCHLIST_API_KEY: str
    app_name: str = "Stock News Sentiment API"
    default_user_agent: str = "StockSentimentBot/1.0 (contact)"

    class Config:
        env_file = ".env"

settings = Settings()
