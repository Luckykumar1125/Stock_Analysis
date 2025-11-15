import { useEffect, useState } from "react";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Loader2, Plus } from "lucide-react";

interface Stock {
  ticker: string;
  name: string;
  price: number;
  change: number; // % change
}

export const Watchlist = () => {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newCompany, setNewCompany] = useState("");
  const [adding, setAdding] = useState(false);

  // Default companies to load
  const defaultCompanies = ["Apple", "Tesla", "Nvidia", "Microsoft"];

  const fetchStock = async (company: string): Promise<Stock | null> => {
    try {
      const res = await axios.get(`http://127.0.0.1:8000/api/stock/${company}`);
      return res.data;
    } catch (err) {
      console.error(`Failed to fetch ${company}`, err);
      return null;
    }
  };

  useEffect(() => {
    const fetchWatchlist = async () => {
      setLoading(true);
      try {
        const results = await Promise.all(defaultCompanies.map(fetchStock));
        setStocks(results.filter((s): s is Stock => s !== null));
      } catch (err) {
        setError("Failed to fetch stock data.");
      } finally {
        setLoading(false);
      }
    };

    fetchWatchlist();
  }, []);

  const handleAddStock = async () => {
    if (!newCompany.trim()) return;
    setAdding(true);
    setError(null);

    const stock = await fetchStock(newCompany.trim());
    if (stock) {
      if (stocks.some((s) => s.ticker === stock.ticker)) {
        setError(`${stock.ticker} is already in your watchlist.`);
      } else {
        setStocks((prev) => [...prev, stock]);
      }
    } else {
      setError(`Couldn't find data for "${newCompany}".`);
    }

    setNewCompany("");
    setAdding(false);
  };

  return (
    <Card className="glass-card border-card-border h-fit">
      <CardHeader>
        <CardTitle className="flex items-center">Your Watchlist</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Input to add new stocks */}
        <div className="flex gap-2 mb-4">
          <Input
            value={newCompany}
            onChange={(e) => setNewCompany(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddStock()}
            placeholder="Enter company name (e.g. Amazon)"
            disabled={adding}
          />
          <Button
            onClick={handleAddStock}
            disabled={!newCompany.trim() || adding}
            className="gradient-primary"
          >
            {adding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
          </Button>
        </div>

        {loading && (
          <div className="flex justify-center items-center h-32">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">
              Fetching live market data...
            </span>
          </div>
        )}

        {!loading && error && (
          <div className="text-center text-destructive py-2 text-sm">{error}</div>
        )}

        {!loading && !error && (
          <div className="max-h-80 overflow-y-auto pr-2 space-y-3 custom-scroll">
            {stocks.map((stock, index) => {
              const isPositive = stock.change >= 0;
              return (
                <div
                  key={stock.ticker}
                  className={`flex justify-between items-center p-3 rounded-lg bg-accent/20 border border-accent hover:bg-accent/30 transition-all duration-300 animate-fade-in`}
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  <div>
                    <div className="font-bold text-primary">{stock.ticker}</div>
                    <div className="text-xs text-muted-foreground">{stock.name}</div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold">₹{stock.price?.toFixed(2)}</div>
                    <div
                      className={`text-xs ${
                        isPositive ? "text-success" : "text-destructive"
                      }`}
                    >
                      {isPositive ? "+" : ""}
                      {stock.change?.toFixed(2)}%
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
