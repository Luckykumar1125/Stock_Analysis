import React, { useEffect, useState } from 'react';
import { 
  ShoppingBag, 
  Calendar, 
  ExternalLink, 
  Loader2, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  RefreshCw
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// --- Types ---
interface SaleEvent {
  store_name: string;
  sale_name: string;
  start_date: string | null;
  end_date: string | null;
  source_url: string;
  confidence: number;
}

interface SalesResponse {
  sales: SaleEvent[];
  last_updated: string;
  source: string;
}

export default function SalesDashboard() {
  const [data, setData] = useState<SalesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSales = async () => {
    setLoading(true);
    setError(null);
    try {
      // Note: This request might take 5-8 seconds due to live scraping
      const response = await fetch('http://127.0.0.1:8000/api/upcoming-sales');
      
      if (!response.ok) {
        throw new Error("Failed to fetch sales data");
      }
      
      const result: SalesResponse = await response.json();
      setData(result);
    } catch (err: any) {
      setError(err.message || "Could not load sales alerts");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSales();
  }, []);

  // Helper to format dates nicely
  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Date TBA";
    return new Date(dateStr).toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  };

  // Helper to determine sale status
  const getStatus = (start: string | null, end: string | null) => {
    if (!start) return { label: "Upcoming", color: "bg-blue-500/10 text-blue-400" };
    const now = new Date();
    const startDate = new Date(start);
    const endDate = end ? new Date(end) : null;

    if (endDate && now > endDate) return { label: "Ended", color: "bg-gray-500/10 text-gray-400" };
    if (now >= startDate) return { label: "Live Now", color: "bg-emerald-500/10 text-emerald-400 animate-pulse" };
    
    // Calc days remaining
    const diffTime = Math.abs(startDate.getTime() - now.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
    
    if (diffDays <= 7) return { label: `Starts in ${diffDays} days`, color: "bg-amber-500/10 text-amber-400" };
    return { label: "Upcoming", color: "bg-primary/10 text-primary" };
  };

  return (
    <div className="w-full space-y-6 animate-in fade-in zoom-in-95 duration-300 pb-8">
      
      {/* Header Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h2 className="text-3xl font-bold gradient-primary bg-clip-text text-transparent flex items-center gap-2">
            <ShoppingBag className="w-8 h-8 text-primary" /> Upcoming Sales Radar
          </h2>
          <p className="text-muted-foreground mt-1">
            Real-time alerts on major e-commerce events across India.
          </p>
        </div>
        
        {data && (
           <div className="flex items-center gap-2 text-xs text-muted-foreground bg-card border border-border/50 px-3 py-1.5 rounded-full">
             {data.source === "Live Web Scrape" ? (
               <CheckCircle2 className="w-3 h-3 text-emerald-500" />
             ) : (
               <Clock className="w-3 h-3 text-amber-500" />
             )}
             Source: {data.source}
             <span className="mx-1">•</span>
             Updated: {data.last_updated.split(' ')[1]}
           </div>
        )}
      </div>

      {/* Main Content */}
      {loading ? (
        <div className="h-[400px] flex flex-col items-center justify-center space-y-4 border-2 border-dashed border-border/30 rounded-xl bg-card/20">
          <Loader2 className="w-10 h-10 animate-spin text-primary" />
          <div className="text-center">
            <p className="font-medium">Scanning e-commerce news...</p>
            <p className="text-sm text-muted-foreground">This usually takes 5-10 seconds.</p>
          </div>
        </div>
      ) : error ? (
        <div className="flex flex-col items-center justify-center h-[300px] text-rose-400 bg-rose-500/5 border border-rose-500/20 rounded-xl">
          <AlertTriangle className="w-10 h-10 mb-2" />
          <p className="font-medium">{error}</p>
          <Button variant="outline" onClick={fetchSales} className="mt-4">
            <RefreshCw className="w-4 h-4 mr-2" /> Retry Search
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data?.sales.length === 0 ? (
            <div className="col-span-full text-center py-12 text-muted-foreground">
              No upcoming sales found at this moment.
            </div>
          ) : (
            data?.sales.map((sale, idx) => {
              const status = getStatus(sale.start_date, sale.end_date);
              return (
                <Card key={idx} className="glass-card border-border/50 hover:border-primary/30 transition-colors group">
                  <CardHeader className="pb-3">
                    <div className="flex justify-between items-start">
                      <Badge variant="outline" className="mb-2">{sale.store_name}</Badge>
                      <span className={`text-[10px] px-2 py-1 rounded-full font-medium uppercase tracking-wider ${status.color}`}>
                        {status.label}
                      </span>
                    </div>
                    <CardTitle className="text-lg leading-tight group-hover:text-primary transition-colors">
                      {sale.sale_name}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Calendar className="w-4 h-4 text-primary/70" />
                        <span>Starts: <span className="text-foreground font-medium">{formatDate(sale.start_date)}</span></span>
                      </div>
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Clock className="w-4 h-4 text-primary/70" />
                        <span>Ends: <span className="text-foreground font-medium">{formatDate(sale.end_date)}</span></span>
                      </div>
                    </div>

                    {sale.source_url && sale.source_url.startsWith('http') && (
                      <Button 
                        variant="ghost" 
                        className="w-full justify-between text-xs h-8 hover:bg-primary/10 hover:text-primary mt-2"
                        onClick={() => window.open(sale.source_url, '_blank')}
                      >
                        Verify Source <ExternalLink className="w-3 h-3" />
                      </Button>
                    )}
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
