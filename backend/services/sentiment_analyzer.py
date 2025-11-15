from transformers import pipeline
from services.news_sentiment import RssNewsFetcher
import yfinance as yf
import asyncio

# Use FinBERT, a finance-specific sentiment model
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="yiyanghkust/finbert-tone",
    tokenizer="yiyanghkust/finbert-tone",
    device=-1
)

async def get_ticker(company_name: str) -> str:
    """Convert company name to ticker using yfinance."""
    try:
        info = yf.Ticker(company_name)
        if info.info.get("symbol"):
            return info.info["symbol"]
    except Exception:
        pass
    # fallback: search all tickers
    tickers = yf.Tickers(company_name)
    return tickers.tickers[0].info["symbol"]

async def analyze_sentiment(query: str, max_articles: int = 10):
    # Convert company name to ticker if needed
    ticker = query.upper()
    try:
        ticker = await get_ticker(query)
    except:
        pass

    news_fetcher = RssNewsFetcher()
    articles = await news_fetcher.fetch(ticker, max_articles=max_articles)

    analyzed_articles = []
    total_score = 0

    for article in articles:
        text = f"{article['title']} {article['snippet']}"
        result = sentiment_analyzer(text[:512])[0]  # truncate to 512 tokens
        label = result["label"].upper()  # FINBERT returns 'positive', 'neutral', 'negative'
        score = result["score"]
        if label == "NEGATIVE":
            score = -score
        elif label == "NEUTRAL":
            score = 0

        total_score += score
        analyzed_articles.append({
            "title": article["title"],
            "link": article["link"],
            "published": str(article["published"]),
            "snippet": article["snippet"],
            "label": label,
            "score": score
        })

    average_score = total_score / len(analyzed_articles) if analyzed_articles else 0
    if average_score > 0.05:
        overall_label = "POSITIVE"
    elif average_score < -0.05:
        overall_label = "NEGATIVE"
    else:
        overall_label = "NEUTRAL"

    return {
        "query": query,
        "analyzed_articles": len(analyzed_articles),
        "average_score": average_score,
        "overall_label": overall_label,
        "per_article": analyzed_articles
    }
