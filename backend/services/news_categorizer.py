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

# Prompt template for categorization
prompt = PromptTemplate(
    input_variables=["title", "excerpt"],
    template="""
You are a financial news categorizer. Categorize the following news into 
one of the categories: Breaking, Earnings, Technology, Global, Energy, Healthcare.

News Title: {title}
Excerpt: {excerpt}

Return only the category name and a very brief summary of the news, no more than 15 words.
Format the response as:
Category: <category name>
Summary: <15-word summary>
"""
)

# Initialize LLMChain for news categorization
chain = RunnableSequence(prompt|llm)

def categorize_news(articles: list[NewsArticle]) -> list[CategorizedNews]:
    """Categorize news articles into predefined categories."""
    categorized = []
    for article in articles:
        # Check if the title and excerpt are available before running the chain
        if article.title and article.excerpt:
            ai_message = chain.invoke({"title": article.title, "excerpt": article.excerpt})
            response_text=ai_message.content
            # This parsing logic will depend on the exact format of the LLM's output
            # A simple approach is to split the text by newlines
            lines = response_text.split('\n')
            category = lines[0].replace("Category:", "").strip() if len(lines) > 0 else "Unknown"
            summary = lines[1].replace("Summary:", "").strip() if len(lines) > 1 else article.excerpt
            
            # Append the new CategorizedNews object
            categorized.append(CategorizedNews(
                category=category,
                title=article.title,
                excerpt=summary, # Use the new, truncated summary
                source=article.source,
                published_at=article.published_at
            ))
    return categorized