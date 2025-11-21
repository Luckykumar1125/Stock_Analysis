from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from core.config import settings
from core.schemas import NewsArticle, CategorizedNews

# Initialize Groq LLM
llm = ChatGroq(
    groq_api_key=settings.GROQ_API_KEY,
    model=settings.MODEL_NAME
)

# UPDATED Prompt: Stricter instructions for the LLM
prompt = PromptTemplate(
    input_variables=["title", "excerpt"],
    template="""
    You are a financial news assistant.
    
    Task 1: Categorize the news into EXACTLY one of these: Breaking, Earnings, Technology, Global, Energy, Healthcare, Finance.
    Task 2: Write a very short summary (maximum 20 words).

    News Title: {title}
    Excerpt: {excerpt}

    Output STRICTLY in this format:
    Category: <category_name>
    Summary: <short_summary>
    """
)

chain = RunnableSequence(prompt | llm)

def categorize_news(articles: list[NewsArticle]) -> list[CategorizedNews]:
    """Categorize news articles and generate short summaries."""
    categorized = []
    
    for article in articles:
        if article.title and article.excerpt:
            try:
                ai_message = chain.invoke({"title": article.title, "excerpt": article.excerpt})
                response_text = ai_message.content
                
                # Default values in case parsing fails
                category = "General"
                summary = article.excerpt[:100] + "..." # Fallback to truncated original text

                # Robust Parsing Logic
                lines = response_text.strip().split('\n')
                for line in lines:
                    clean_line = line.strip()
                    if clean_line.startswith("Category:"):
                        category = clean_line.replace("Category:", "").strip()
                    elif clean_line.startswith("Summary:"):
                        summary = clean_line.replace("Summary:", "").strip()

                # Append the result
                categorized.append(CategorizedNews(
                    category=category,
                    title=article.title,
                    excerpt=summary, # This will now be the short AI summary
                    source=article.source,
                    published_at=article.published_at
                ))
            except Exception as e:
                print(f"Error categorizing article '{article.title}': {e}")
                # Append original if AI fails
                categorized.append(CategorizedNews(
                    category="Uncategorized",
                    title=article.title,
                    excerpt=article.excerpt,
                    source=article.source,
                    published_at=article.published_at
                ))
                
    return categorized