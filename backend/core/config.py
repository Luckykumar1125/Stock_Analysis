import os
import torch
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # --- Env Vars (Loaded from .env) ---
    NEWS_API_KEY: str
    GROQ_API_KEY: str
    WATCHLIST_API_KEY: str
    
    # --- Default Defaults ---
    app_name: str = "Stock News Sentiment API"
    default_user_agent: str = "StockSentimentBot/1.0 (contact)"
    
    # --- Paths ---
    # Note: Ensure these paths exist or use absolute paths if running from different dirs
    BANK_DB_PATH: str = "Stock_Analysis/backend/bank_statements.db"
    DB_PATH: str = "Stock_Analysis/backend/sentiment.db"

    # --- LLM Settings ---
    MODEL_NAME: str = "meta-llama/llama-guard-4-12b" # Your Llama model
    
    # --- External APIs ---
    NEWS_API_URL: str = "https://newsapi.org/v2/top-headlines?category=business&language=en&pageSize=20"
    NEWS_API_URL_INSIGHTS: str ="https://newsapi.org/v2/everything"

    # --- FinBERT Sentiment Settings (CPU Optimized) ---
    FINBERT_MODEL_NAME: str = "ProsusAI/finbert"
    
    @property
    def DEVICE(self):
        # Force CPU usage
        return torch.device("cpu")

    @property
    def SENTIMENT_MAP(self):
        return {0: 'positive', 1: 'negative', 2: 'neutral'}

    # --- Pydantic Internal Config ---
    class Config:
        env_file = ".env"
        extra = "ignore" # Ignores extra fields in .env file if they aren't defined above

# Instantiate the settings
settings = Settings()