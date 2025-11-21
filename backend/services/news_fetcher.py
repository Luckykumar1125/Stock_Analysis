import requests
from core.config import settings
from core.schemas import NewsArticle

def fetch_news() -> list[NewsArticle]:
    """Fetch financial news from India and the world using NewsData.io."""

    combined_articles = []

    # Helper function to fetch and parse articles from a given URL
    def fetch_articles_from_url(url: str) -> list[NewsArticle]:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data.get("results"), list):
                print(f"API response missing 'results' key. Response: {data}")
                return []
                
            articles = []
            for item in data["results"]:
                # We treat 'description' as the raw excerpt
                articles.append(NewsArticle(
                    title=item.get("title", "No title"),
                    excerpt=item.get("description") or item.get("content") or "No content",
                    source=item.get("source_id", "Unknown"),
                    published_at=item.get("pubDate", "")
                ))
            return articles
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return []

    # Fetch Indian financial news (Increased size to 10)
    indian_url = f"https://newsdata.io/api/1/latest?country=in&category=business&size=10&apikey={settings.WATCHLIST_API_KEY}"
    combined_articles.extend(fetch_articles_from_url(indian_url))

    # Fetch international financial news (US)
    international_url = f"https://newsdata.io/api/1/latest?country=us&category=business&size=5&apikey={settings.WATCHLIST_API_KEY}"
    combined_articles.extend(fetch_articles_from_url(international_url))

    return combined_articles