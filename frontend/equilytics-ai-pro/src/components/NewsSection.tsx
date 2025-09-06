import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// Define NewsItem interface for frontend
interface NewsItem {
  category: string;
  title: string;
  excerpt: string;
  meta: string;
  featured?: boolean;
}

export const NewsSection = () => {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/news"); // 🔗 your FastAPI backend
        const data = await res.json();

        // Transform backend `items` into NewsItem[]
        const formatted: NewsItem[] = data.items.map(
          (item: any, index: number) => ({
            category: item.category || "General",
            title: item.title,
            excerpt: item.excerpt,
            meta: `${new Date(item.published_at).toLocaleString()} • ${item.source}`,
            featured: index === 0 // highlight first article
          })
        );

        setNews(formatted);
      } catch (error) {
        console.error("Error fetching news:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, []);

  const getCategoryColor = (category: string) => {
    switch (category.toLowerCase()) {
      case "breaking":
        return "bg-destructive/20 text-destructive border-destructive/30";
      case "earnings":
        return "bg-success/20 text-success border-success/30";
      case "technology":
        return "bg-primary/20 text-primary border-primary/30";
      case "energy":
        return "bg-yellow-200 text-yellow-800 border-yellow-400";
      case "global":
        return "bg-blue-200 text-blue-800 border-blue-400";
      default:
        return "bg-muted/20 text-muted-foreground border-muted/30";
    }
  };

  if (loading) {
    return (
      <Card className="glass-card border-card-border">
        <CardHeader>
          <CardTitle>📰 Loading Market News...</CardTitle>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="glass-card border-card-border">
      <CardHeader>
        <CardTitle className="flex items-center">
          📰 Latest Market News & Analysis
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {news.map((item, index) => (
            <div
              key={index}
              className={`p-4 rounded-lg border transition-all duration-300 hover:shadow-card cursor-pointer animate-slide-up ${
                item.featured
                  ? "col-span-full bg-primary/5 border-primary/20 shadow-primary"
                  : "bg-accent/10 border-accent hover:bg-accent/20"
              }`}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div
                className={`inline-block px-2 py-1 rounded text-xs font-medium border mb-3 ${getCategoryColor(
                  item.category
                )}`}
              >
                {item.category}
              </div>
              <h4
                className={`font-bold mb-2 leading-tight ${
                  item.featured ? "text-lg" : "text-base"
                }`}
              >
                {item.title}
              </h4>
              <p className="text-sm text-muted-foreground mb-3 leading-relaxed">
                {item.excerpt}
              </p>
              <div className="text-xs text-muted-foreground">{item.meta}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

