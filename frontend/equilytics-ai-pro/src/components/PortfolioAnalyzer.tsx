import React, { useState } from 'react';
import { 
  Plus, 
  Trash2, 
  TrendingUp, 
  AlertTriangle, 
  PieChart as PieIcon, 
  Activity, 
  BrainCircuit, 
  IndianRupee,
  ArrowRight
} from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

// --- Types ---
interface StockPosition {
  id: string;
  symbol: string;
  purchase_date: string;
  quantity: number;
  purchase_price?: number;
}

interface HoldingMetric {
  symbol: string;
  current_price: number;
  total_gain_loss_pct: number;
  cagr: number;
  volatility_annualized: number;
  beta: number;
  sharpe_ratio: number;
  weight_in_portfolio: number;
}

interface AnalysisResult {
  total_value: number;
  total_gain_loss_pct: number;
  portfolio_volatility: number;
  diversification_index: number;
  holdings: HoldingMetric[];
}

interface APIResponse {
  analysis: AnalysisResult;
  ai_rebalancing_advice: string;
}

// --- Markdown Renderer Component ---
const MarkdownRenderer = ({ content }: { content: string }) => {
  // Simple parser for the specific format returned by the LLM
  const parseBold = (text: string) => {
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <span key={index} className="font-bold text-foreground">{part.slice(2, -2)}</span>;
      }
      return part;
    });
  };

  const lines = content.split('\n');

  return (
    <div className="space-y-1 text-sm">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-3" />;
        
        // Headers (### Title)
        if (trimmed.startsWith('###')) {
          return (
            <h3 key={i} className="text-lg font-semibold text-primary mt-5 mb-3 pb-2 border-b border-primary/10 flex items-center gap-2">
               {trimmed.replace(/^###\s*/, '')}
            </h3>
          );
        }
        
        // List items (* Item or - Item)
        if (trimmed.startsWith('* ') || trimmed.startsWith('- ')) {
          const content = trimmed.replace(/^[\*\-]\s*/, '');
          return (
            <div key={i} className="flex items-start gap-3 pl-2 mb-2">
              <div className="min-w-[6px] h-[6px] rounded-full bg-primary/60 mt-2" />
              <p className="text-muted-foreground leading-relaxed">
                {parseBold(content)}
              </p>
            </div>
          );
        }

        // Standard text
        return (
          <p key={i} className="text-muted-foreground leading-relaxed mb-1">
            {parseBold(trimmed)}
          </p>
        );
      })}
    </div>
  );
};

export default function PortfolioAnalyzer() {
  // --- State ---
  const [positions, setPositions] = useState<StockPosition[]>([
    { id: '1', symbol: '', purchase_date: '', quantity: 0 }
  ]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<APIResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // --- Handlers ---
  const addRow = () => {
    setPositions([
      ...positions,
      { id: crypto.randomUUID(), symbol: '', purchase_date: '', quantity: 0 }
    ]);
  };

  const removeRow = (id: string) => {
    if (positions.length > 1) {
      setPositions(positions.filter(p => p.id !== id));
    }
  };

  const updateRow = (id: string, field: keyof StockPosition, value: any) => {
    setPositions(positions.map(p => 
      p.id === id ? { ...p, [field]: value } : p
    ));
  };

  const analyzePortfolio = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    // Basic Validation
    const validPositions = positions.filter(p => p.symbol && p.quantity > 0 && p.purchase_date);
    if (validPositions.length === 0) {
      setError("Please enter at least one valid stock position.");
      setLoading(false);
      return;
    }

    try {
      // Payload formatting for backend
      const payload = {
        positions: validPositions.map(p => ({
          symbol: p.symbol,
          purchase_date: p.purchase_date,
          quantity: Number(p.quantity),
          purchase_price: p.purchase_price ? Number(p.purchase_price) : null
        })),
        benchmark: "^GSPC",
        risk_free_rate: 0.04
      };

      const response = await fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Analysis failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- Render Helpers ---
  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val);

  const formatPct = (val: number) => `${val > 0 ? '+' : ''}${val.toFixed(2)}%`;

  // --- Main Render ---
  return (
    <div className="w-full space-y-8 animate-in fade-in zoom-in-95 duration-300">
      {/* Header Section */}
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-bold gradient-primary bg-clip-text text-transparent">
          Portfolio AI Analyzer
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Enter your holdings below. Our AI will calculate risk metrics, diversification scores, and suggest rebalancing strategies.
        </p>
      </div>

      {/* Input Section */}
      <Card className="glass-card border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Plus className="w-5 h-5 text-primary" /> Add Holdings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4">
            {positions.map((pos, index) => (
              <div key={pos.id} className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end animate-slide-up" style={{ animationDelay: `${index * 0.05}s` }}>
                <div className="md:col-span-3">
                  <label className="text-xs text-muted-foreground mb-1 block">Ticker Symbol</label>
                  <Input 
                    placeholder="e.g. AAPL, RELIANCE.NS" 
                    value={pos.symbol}
                    onChange={(e) => updateRow(pos.id, 'symbol', e.target.value.toUpperCase())}
                    className="bg-background/50"
                  />
                </div>
                <div className="md:col-span-3">
                  <label className="text-xs text-muted-foreground mb-1 block">Purchase Date</label>
                  <Input 
                    type="date" 
                    value={pos.purchase_date}
                    onChange={(e) => updateRow(pos.id, 'purchase_date', e.target.value)}
                    className="bg-background/50"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="text-xs text-muted-foreground mb-1 block">Quantity</label>
                  <Input 
                    type="number" 
                    placeholder="0"
                    value={pos.quantity || ''}
                    onChange={(e) => updateRow(pos.id, 'quantity', Number(e.target.value))}
                    className="bg-background/50"
                  />
                </div>
                <div className="md:col-span-3">
                  <label className="text-xs text-muted-foreground mb-1 block">Buy Price (Optional)</label>
                  <Input 
                    type="number" 
                    placeholder="Auto-fetch if empty"
                    value={pos.purchase_price || ''}
                    onChange={(e) => updateRow(pos.id, 'purchase_price', Number(e.target.value))}
                    className="bg-background/50"
                  />
                </div>
                <div className="md:col-span-1">
                  <Button 
                    variant="ghost" 
                    size="icon" 
                    onClick={() => removeRow(pos.id)}
                    className="text-destructive hover:text-destructive/80 hover:bg-destructive/10"
                    disabled={positions.length === 1}
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
          
          <div className="flex justify-between items-center pt-4 border-t border-border/30">
            <Button variant="outline" onClick={addRow} className="gap-2 hover:bg-primary/10 hover:text-primary border-dashed">
              <Plus className="w-4 h-4" /> Add Another Stock
            </Button>
            <Button 
              onClick={analyzePortfolio} 
              disabled={loading}
              className="gradient-primary px-8 shadow-lg hover:shadow-primary/25 transition-all"
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <Activity className="w-4 h-4 animate-spin" /> Analyzing...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                   Analyze Portfolio <ArrowRight className="w-4 h-4" />
                </span>
              )}
            </Button>
          </div>

          {error && (
            <div className="p-4 mt-4 bg-destructive/10 border border-destructive/20 rounded-lg text-destructive flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" /> {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Results View */}
      {result && (
        <div className="space-y-8 animate-in slide-in-from-bottom-10 duration-500">
          
          {/* 1. Top Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard 
              title="Total Value" 
              value={formatCurrency(result.analysis.total_value)} 
              icon={<IndianRupee className="w-5 h-5 text-emerald-400" />}
              subtext={`${formatPct(result.analysis.total_gain_loss_pct)} all time`}
              positive={result.analysis.total_gain_loss_pct >= 0}
            />
            <MetricCard 
              title="Volatility (Risk)" 
              value={(result.analysis.portfolio_volatility * 100).toFixed(2) + "%"} 
              icon={<Activity className="w-5 h-5 text-orange-400" />}
              subtext="Annualized Standard Deviation"
            />
            <MetricCard 
              title="Sharpe Ratio" 
              value={result.analysis.holdings.length > 0 ? result.analysis.holdings[0].sharpe_ratio.toFixed(2) : "N/A"} // Simplified for demo, usually calculated at portfolio level
              icon={<TrendingUp className="w-5 h-5 text-blue-400" />}
              subtext="Risk-Adjusted Return"
            />
            <MetricCard 
              title="Diversification Score" 
              value={(result.analysis.diversification_index * 10).toFixed(1) + "/10"} 
              icon={<PieIcon className="w-5 h-5 text-purple-400" />}
              subtext={result.analysis.diversification_index > 0.7 ? "Well Diversified" : "Concentrated"}
              positive={result.analysis.diversification_index > 0.5}
            />
          </div>

          {/* 2. AI Advisor Section */}
          <Card className="glass-card border-primary/20 overflow-hidden relative">
            <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-primary to-purple-600" />
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-primary">
                <BrainCircuit className="w-6 h-6" /> AI Rebalancing Strategy
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Updated to use the new MarkdownRenderer */}
              <MarkdownRenderer content={result.ai_rebalancing_advice} />
            </CardContent>
          </Card>

          {/* 4. Detailed Holdings Table */}
          <Card className="glass-card border-border/50 overflow-hidden">
            <CardHeader><CardTitle>Holdings Detail</CardTitle></CardHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs uppercase bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="px-6 py-3">Symbol</th>
                    <th className="px-6 py-3">Weight</th>
                    <th className="px-6 py-3">Beta</th>
                    <th className="px-6 py-3">Gain/Loss</th>
                    <th className="px-6 py-3">CAGR</th>
                  </tr>
                </thead>
                <tbody>
                  {result.analysis.holdings.map((h, i) => (
                    <tr key={h.symbol} className="border-b border-border/50 hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4 font-medium">{h.symbol}</td>
                      <td className="px-6 py-4">{(h.weight_in_portfolio * 100).toFixed(2)}%</td>
                      <td className="px-6 py-4">{h.beta.toFixed(2)}</td>
                      <td className={`px-6 py-4 font-bold ${h.total_gain_loss_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {formatPct(h.total_gain_loss_pct)}
                      </td>
                      <td className="px-6 py-4">{h.cagr.toFixed(2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

        </div>
      )}
    </div>
  );
}

// --- Sub-component for metrics ---
function MetricCard({ title, value, icon, subtext, positive }: any) {
  return (
    <Card className="glass-card border-border/50 hover:bg-white/5 transition-colors">
      <CardContent className="p-6 flex flex-col justify-between h-full">
        <div className="flex justify-between items-start mb-4">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <h3 className="text-2xl font-bold mt-1">{value}</h3>
          </div>
          <div className="p-2 bg-white/5 rounded-lg">
            {icon}
          </div>
        </div>
        {subtext && (
          <p className={`text-xs ${positive === undefined ? 'text-muted-foreground' : positive ? 'text-emerald-400' : 'text-rose-400'}`}>
            {subtext}
          </p>
        )}
      </CardContent>
    </Card>
  );
}