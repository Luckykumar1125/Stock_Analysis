# import os
# from datetime import datetime, timedelta
# from typing import List
# import yfinance as yf
# import praw
# import requests
# from groq import Groq
# from fastapi import HTTPException
# from core.schemas import MarketPrediction, TrendingTicker

# groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# # -------------------------------
# # Reddit client
# # -------------------------------
# reddit = praw.Reddit(
#     client_id=os.getenv("REDDIT_CLIENT_ID"),
#     client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
#     user_agent=os.getenv("REDDIT_USER_AGENT"),
# )

# # -------------------------------
# # Helper functions
# # -------------------------------
# def fetch_news(ticker: str, api_key: str) -> List[str]:
#     """Fetch news from free NewsAPI.org"""
#     url = f"https://newsapi.org/v2/everything?q={ticker}&language=en&pageSize=20&apiKey={api_key}"
#     r = requests.get(url)
#     data = r.json()
#     if "articles" not in data:
#         return []
#     return [f"{a['title']}. {a.get('description', '')}" for a in data["articles"]]

# def fetch_reddit(ticker: str, limit: int = 50) -> List[str]:
#     posts = []
#     for submission in reddit.subreddit("stocks").search(ticker, limit=limit):
#         posts.append(submission.title)
#         try:
#             submission.comments.replace_more(limit=0)
#             for c in submission.comments.list():
#                 posts.append(c.body)
#         except Exception:
#             pass
#     return posts

# def fetch_stock_price(ticker: str) -> float:
#     stock = yf.Ticker(ticker)
#     data = stock.history(period="1d")
#     if data.empty:
#         raise HTTPException(status_code=404, detail="Stock not found")
#     return float(data['Close'][-1])

# def analyze_sentiment(texts: List[str]) -> float:
#     prompt = (
#         "You are a financial sentiment analyzer. Given the following text snippets "
#         "about a stock, output a sentiment score between -1 (very negative) and +1 (very positive).\n\n"
#         + "\n---\n".join(texts)
#     )
#     response = groq_client.chat.completions.create(
#         model="meta-llama/llama-4-maverick-17b-128e-instruct",
#         messages=[
#             {"role": "system", "content": "You are a financial sentiment analyst."},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=256,
#         temperature=0
#     )
#     try:
#         return float(response.choices[0].message.content.split()[0])
#     except Exception:
#         return 0.0  # fallback

# def identify_trending_tickers(texts: List[str]) -> List[TrendingTicker]:
#     import re
#     from collections import Counter
#     pattern = re.compile(r"\$[A-Z]{1,5}\b")
#     mentions = []
#     for t in texts:
#         mentions += pattern.findall(t)
#     counter = Counter(mentions)
#     trending = []
#     for t, c in counter.most_common(5):
#         ticker = t.lstrip("$")
#         trending.append(TrendingTicker(ticker=ticker, sentiment_score=0.0, trend_percentage=(c/len(texts))*100))
#     return trending

# def generate_market_prediction(ticker: str, sentiment: float, price: float) -> MarketPrediction:
#     prompt = (
#         f"The sentiment score for ${ticker} is {sentiment:.2f} and current price is {price:.2f}. "
#         "Provide a 1-2 sentence market prediction."
#     )
#     response = groq_client.chat.completions.create(
#         model="meta-llama/llama-4-maverick-17b-128e-instruct",
#         messages=[
#             {"role": "system", "content": "You are a financial market analyst."},
#             {"role": "user", "content": prompt}
#         ],
#         max_tokens=128,
#         temperature=0
#     )
#     return MarketPrediction(message=response.choices[0].message.content.strip())
