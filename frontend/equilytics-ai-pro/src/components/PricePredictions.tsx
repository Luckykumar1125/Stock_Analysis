import React, { useState } from 'react';
import { 
  LineChart, 
  Search, 
  Loader2, 
  TrendingUp, 
  TrendingDown, 
  IndianRupee, 
  Calendar,
  AlertCircle 
} from 'lucide-react';

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

// --- Types ---

interface ForecastValue {
  date: string;
  price: number;
  lower: number;
  upper: number;
}

interface StockSummary {
  company_name: string;
  ticker: string;
  current_price: number;
  predicted_price: number;
  growth_percent: number;
}

interface StockResponse {
  ticker: string;
  company_name: string;
  image_base64: string;
  forecast_values: ForecastValue[];
  summary: StockSummary;
}

export default function StockDashboard() {
  // --- State ---
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<StockResponse | null>(null);

  // --- Handlers ---
  const handlePredict = async () => {
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/predict-stock', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // We send 'query' as 'ticker' because the backend accepts 'ticker' field but handles names too
        body: JSON.stringify({ ticker: query, days_ahead: 30 }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to fetch forecast. Please check the company name.");
      }

      const result: StockResponse = await response.json();
      setData(result);

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handlePredict();
    }
  };

  // Helper to format currency
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val);

  // --- Render ---
  return (
    <div className="min-h-screen w-full bg-background p-6 md:p-12 animate-in fade-in zoom-in-95 duration-300">
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* 1. Hero Section */}
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center p-3 bg-primary/10 rounded-full mb-2">
            <LineChart className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight gradient-primary bg-clip-text text-transparent">
            Market Oracle
          </h1>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            AI-powered stock price forecasting. Enter a company name to generate a 30-day prediction model.
          </p>
        </div>

        {/* 2. Search Section */}
        <Card className="max-w-2xl mx-auto border-2 border-primary/20 shadow-lg shadow-primary/5">
          <CardContent className="p-2">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-3 h-5 w-5 text-muted-foreground" />
                <Input 
                  placeholder="Enter Company Name (e.g. Zomato, Reliance, Tesla)..." 
                  value={query} 
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="pl-10 h-12 text-lg border-transparent focus-visible:ring-0 bg-transparent"
                />
              </div>
              <Button 
                onClick={handlePredict} 
                disabled={!query || loading} 
                className="h-12 px-8 text-lg font-medium transition-all hover:scale-105"
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : "Predict"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 3. Error Display */}
        {error && (
          <div className="max-w-md mx-auto flex items-center gap-2 p-4 text-rose-400 bg-rose-500/10 rounded-lg border border-rose-500/20 animate-slide-up">
            <AlertCircle className="w-5 h-5" />
            <p>{error}</p>
          </div>
        )}

        {/* 4. Results Dashboard */}
        {data && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up">
            
            {/* Left Column: Chart & Identity */}
            <div className="lg:col-span-2 space-y-6">
              <Card className="overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="border-b border-border/50">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-2xl">{data.summary.company_name}</CardTitle>
                      <CardDescription className="flex items-center gap-2 mt-1">
                        <span className="font-mono bg-muted px-2 py-0.5 rounded text-xs text-foreground">
                          {data.summary.ticker}
                        </span>
                        <span>• 30 Day Forecast Model</span>
                      </CardDescription>
                    </div>
                    <div className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold ${
                      data.summary.growth_percent >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                    }`}>
                      {data.summary.growth_percent >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                      {data.summary.growth_percent > 0 ? '+' : ''}{data.summary.growth_percent}%
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <img 
                    src={`data:image/png;base64,${data.image_base64}`} 
                    alt="Forecast Chart" 
                    className="w-full h-auto object-cover hover:scale-[1.01] transition-transform duration-500"
                  />
                </CardContent>
              </Card>
            </div>

            {/* Right Column: Stats & Data */}
            <div className="space-y-6">
              
              {/* Key Metrics Cards */}
              <div className="grid grid-cols-1 gap-4">
                <Card className="bg-card/50 border-border/50">
                  <CardContent className="p-6 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Current Price</p>
                      <h3 className="text-3xl font-bold mt-1">{formatCurrency(data.summary.current_price)}</h3>
                    </div>
                    <div className="p-3 bg-muted rounded-full">
                      <IndianRupee className="w-6 h-6 opacity-70" />
                    </div>
                  </CardContent>
                </Card>

                <Card className={`border-border/50 ${
                  data.summary.growth_percent >= 0 ? 'bg-emerald-500/5 border-emerald-500/20' : 'bg-rose-500/5 border-rose-500/20'
                }`}>
                  <CardContent className="p-6 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Predicted Price</p>
                      <h3 className={`text-3xl font-bold mt-1 ${
                        data.summary.growth_percent >= 0 ? 'text-emerald-400' : 'text-rose-400'
                      }`}>
                        {formatCurrency(data.summary.predicted_price)}
                      </h3>
                    </div>
                    <div className={`p-3 rounded-full ${
                      data.summary.growth_percent >= 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                    }`}>
                      <TrendingUp className="w-6 h-6" />
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Daily Breakdown Table */}
              <Card className="border-border/50 bg-card/50 flex flex-col h-[400px]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-primary" /> Daily Forecast Breakdown
                  </CardTitle>
                </CardHeader>
                <div className="flex-1 overflow-y-auto p-0 custom-scrollbar">
                  <table className="w-full text-sm text-left">
                    <thead className="text-xs uppercase bg-muted/50 text-muted-foreground sticky top-0 backdrop-blur-md">
                      <tr>
                        <th className="px-6 py-3">Date</th>
                        <th className="px-6 py-3 text-right">Forecast</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {data.forecast_values.map((val, i) => (
                        <tr key={i} className="hover:bg-white/5 transition-colors">
                          <td className="px-6 py-3 text-muted-foreground font-mono text-xs">
                            {val.date}
                          </td>
                          <td className="px-6 py-3 text-right font-medium text-emerald-400">
                            {formatCurrency(val.price)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

            </div>
          </div>
        )}
      </div>
    </div>
  );
}