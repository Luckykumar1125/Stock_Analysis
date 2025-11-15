import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function SentimentModal({ onClose }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const fetchSentiment = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/sentiment?query=${query}`);
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error("Error fetching sentiment:", err);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const chartData = result?.per_article?.reduce((acc, article) => {
    const label = article.label || "NEUTRAL";
    acc[label] = (acc[label] || 0) + 1;
    return acc;
  }, {}) || {};

  const barData = Object.keys(chartData).map((key) => ({
    label: key,
    count: chartData[key],
  }));

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-4xl w-full overflow-hidden">
        <DialogHeader>
          <DialogTitle>Sentiment Analysis</DialogTitle>
        </DialogHeader>

        <div className="flex gap-2 mb-4">
          <Input
            placeholder="Enter stock symbol or company name (e.g. AAPL or Apple)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1"

          />
          <Button onClick={fetchSentiment} disabled={loading || !query}>
            {loading ? "Analyzing..." : "Analyze"}
          </Button>
        </div>

        {result && (
          <>
            <h3 className="text-lg font-semibold mb-2">
              Overall Sentiment:{" "}
              <span
                className={
                  result.overall_label === "POSITIVE"
                    ? "text-green-500"
                    : result.overall_label === "NEGATIVE"
                    ? "text-red-500"
                    : "text-gray-500"
                }
              >
                {result.overall_label || "NEUTRAL"}
              </span>
            </h3>

            {barData.length > 0 ? (
              <div className="h-48 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={barData}>
                    <XAxis dataKey="label" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-center text-muted-foreground mb-6">
                No sentiment data available.
              </p>
            )}

            {result.per_article && result.per_article.length > 0 ? (
              <div className="max-h-80 overflow-y-auto space-y-3">
                {result.per_article.map((article, i) => (
                  <div
                    key={i}
                    className="border p-3 rounded-lg hover:bg-muted transition"
                  >
                    <a
                      href={article.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-medium text-primary hover:underline"
                    >
                      {article.title}
                    </a>
                    <p className="text-xs text-muted-foreground">
                      {article.published
                        ? new Date(article.published).toLocaleString()
                        : "Unknown Date"}{" "}
                      • {article.label || "NEUTRAL"}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-center text-muted-foreground">
                No articles found.
              </p>
            )}
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
