import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  FileText, 
  TrendingUp, 
  TrendingDown, 
  IndianRupee, 
  AlertCircle,
  CheckCircle2,
  PieChart,
  BarChart3,
  Loader2
} from 'lucide-react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

// --- Interfaces ---

interface Transaction {
  date: string;
  time: string;
  transaction_type: "Paid to" | "Received from";
  name: string;
  amount: number;
}

interface StatementStats {
  totalIncome: number;
  totalExpense: number;
  netBalance: number;
  transactionCount: number;
}

// Matches the response from /analytics/embedded
interface AnalyticsData {
  summary: {
    total_spend: number;
    amount_per_category: Record<string, number>;
  };
  pie_png_base64: string;
  bar_png_base64: string;
}

export default function BalanceSheetAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false); // New loading state for analytics
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- Handlers ---

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
      // Reset previous results when file changes
      setTransactions([]);
      setAnalytics(null);
    }
  };

  const fetchAnalytics = async () => {
    setAnalyzing(true);
    try {
      // Call the embedded analytics endpoint
      const response = await fetch('http://127.0.0.1:8000/analytics/embedded?use_llm=true');
      
      if (!response.ok) {
        throw new Error("Failed to fetch analytics");
      }

      const data: AnalyticsData = await response.json();
      setAnalytics(data);
    } catch (err) {
      console.error("Analytics error:", err);
      // We don't set main error here to avoid hiding the transaction list if analytics fails
    } finally {
      setAnalyzing(false);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Please select a PDF file first.");
      return;
    }

    setLoading(true);
    setError(null);
    setAnalytics(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://127.0.0.1:8000/parse-bank-statement', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to parse the statement. Please check the file format.");
      }

      const jsonResponse = await response.json();
      
      if (jsonResponse.data && Array.isArray(jsonResponse.data)) {
        setTransactions(jsonResponse.data);
        
        // 2. Immediately fetch analytics after successful parse
        // We wait for the DB write in the backend to finish (implied by response return)
        await fetchAnalytics(); 
        
      } else {
        throw new Error("Invalid response format from server.");
      }

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // --- Helpers ---

  const calculateStats = (data: Transaction[]): StatementStats => {
    return data.reduce(
      (acc, curr) => {
        if (curr.amount > 0) {
          acc.totalIncome += curr.amount;
        } else {
          acc.totalExpense += Math.abs(curr.amount);
        }
        acc.netBalance += curr.amount;
        return acc;
      },
      { totalIncome: 0, totalExpense: 0, netBalance: 0, transactionCount: data.length }
    );
  };

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(Math.abs(val));

  const stats = calculateStats(transactions);

  return (
    <div className="w-full space-y-8 animate-in fade-in zoom-in-95 duration-300 pb-12">
      
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-3xl font-bold gradient-primary bg-clip-text text-transparent">
          Bank Statement Analyzer
        </h2>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          AI-powered financial analysis. Upload your statement to detect transactions and categorize spending.
        </p>
      </div>

      {/* Upload Section */}
      <Card className="glass-card border-border/50 border-dashed border-2 max-w-3xl mx-auto">
        <CardContent className="flex flex-col items-center justify-center py-8 space-y-4">
          <div className="p-4 bg-primary/10 rounded-full">
            <UploadCloud className="w-10 h-10 text-primary" />
          </div>
          
          <div className="text-center">
             <h3 className="text-lg font-medium">Upload PDF Statement</h3>
             <p className="text-sm text-muted-foreground mt-1">We support standard bank PDF formats</p>
          </div>

          <input 
            type="file" 
            accept=".pdf" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            className="hidden" 
          />

          <div className="flex gap-3">
            <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
              {file ? "Change File" : "Select File"}
            </Button>
            <Button 
              className="gradient-primary" 
              onClick={handleUpload} 
              disabled={!file || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Processing...
                </>
              ) : "Analyze Statement"}
            </Button>
          </div>

          {file && (
            <div className="flex items-center gap-2 text-sm text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full">
              <FileText className="w-4 h-4" />
              {file.name}
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-rose-500 bg-rose-500/10 px-3 py-1 rounded-full">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Content Area */}
      {transactions.length > 0 && (
        <Tabs defaultValue="overview" className="w-full max-w-6xl mx-auto">
          <div className="flex justify-center mb-6">
            <TabsList className="grid w-[400px] grid-cols-2">
              <TabsTrigger value="overview">Overview & Charts</TabsTrigger>
              <TabsTrigger value="transactions">Detailed Transactions</TabsTrigger>
            </TabsList>
          </div>

          {/* --- Tab 1: Overview & Analytics --- */}
          <TabsContent value="overview" className="space-y-6 animate-slide-up">
            
            {/* Summary Statistics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="glass-card border-border/50 bg-emerald-500/5">
                <CardContent className="p-6 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Income</p>
                    <h3 className="text-2xl font-bold text-emerald-400 mt-1">{formatCurrency(stats.totalIncome)}</h3>
                  </div>
                  <div className="p-3 bg-emerald-500/10 rounded-lg">
                    <TrendingUp className="w-6 h-6 text-emerald-400" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-card border-border/50 bg-rose-500/5">
                <CardContent className="p-6 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Total Expenses</p>
                    <h3 className="text-2xl font-bold text-rose-400 mt-1">{formatCurrency(stats.totalExpense)}</h3>
                  </div>
                  <div className="p-3 bg-rose-500/10 rounded-lg">
                    <TrendingDown className="w-6 h-6 text-rose-400" />
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-card border-border/50">
                <CardContent className="p-6 flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Net Balance</p>
                    <h3 className={`text-2xl font-bold mt-1 ${stats.netBalance >= 0 ? 'text-foreground' : 'text-rose-400'}`}>
                      {stats.netBalance >= 0 ? '+' : '-'}{formatCurrency(stats.netBalance)}
                    </h3>
                  </div>
                  <div className="p-3 bg-primary/10 rounded-lg">
                    <IndianRupee className="w-6 h-6 text-primary" />
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Analytics Charts Section */}
            {analyzing ? (
               <div className="h-64 flex flex-col items-center justify-center text-muted-foreground space-y-2">
                  <Loader2 className="w-8 h-8 animate-spin text-primary" />
                  <p>Generating spending insights with AI...</p>
               </div>
            ) : analytics ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Category Pie Chart */}
                <Card className="glass-card border-border/50">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <PieChart className="w-4 h-4 text-primary" /> Spending by Category
                    </CardTitle>
                    <CardDescription>AI-categorized breakdown of expenses</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col items-center">
                    <img 
                      src={`data:image/png;base64,${analytics.pie_png_base64}`} 
                      alt="Category Pie Chart" 
                      className="rounded-lg max-h-[300px] object-contain"
                    />
                    {/* Mini Legend/List below chart */}
                    <div className="w-full mt-6 grid grid-cols-2 gap-2 text-sm">
                        {analytics.summary.amount_per_category && Object.entries(analytics.summary.amount_per_category)
                          .sort(([,a], [,b]) => b - a) // Sort by amount desc
                          .slice(0, 6) // Top 6
                          .map(([category, amount]) => (
                          <div key={category} className="flex justify-between items-center p-2 bg-muted/30 rounded">
                            <span className="truncate font-medium">{category}</span>
                            <span>{formatCurrency(amount)}</span>
                          </div>
                        ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Top Merchants Bar Chart */}
                <Card className="glass-card border-border/50">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      <BarChart3 className="w-4 h-4 text-primary" /> Top Merchants
                    </CardTitle>
                    <CardDescription>Where your money is going the most</CardDescription>
                  </CardHeader>
                  <CardContent className="flex justify-center items-center">
                    <img 
                      src={`data:image/png;base64,${analytics.bar_png_base64}`} 
                      alt="Top Merchants Bar Chart" 
                      className="rounded-lg max-h-[300px] w-full object-contain"
                    />
                  </CardContent>
                </Card>
              </div>
            ) : (
              <div className="text-center py-10 text-muted-foreground">
                <p>Analytics could not be loaded.</p>
              </div>
            )}

          </TabsContent>

          {/* --- Tab 2: Detailed Transactions --- */}
          <TabsContent value="transactions">
            <Card className="glass-card border-border/50 overflow-hidden">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5 text-primary" /> Transaction History
                  <span className="text-sm font-normal text-muted-foreground ml-2">({stats.transactionCount} items)</span>
                </CardTitle>
              </CardHeader>
              <div className="max-h-[600px] overflow-y-auto custom-scrollbar">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs uppercase bg-muted/50 text-muted-foreground sticky top-0 z-10 backdrop-blur-md">
                    <tr>
                      <th className="px-6 py-3">Date</th>
                      <th className="px-6 py-3">Description</th>
                      <th className="px-6 py-3">Type</th>
                      <th className="px-6 py-3 text-right">Amount</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/50">
                    {transactions.map((t, i) => (
                      <tr key={i} className="hover:bg-white/5 transition-colors">
                        <td className="px-6 py-4 text-muted-foreground">
                          <div className="font-medium text-foreground">{t.date}</div>
                          <div className="text-xs opacity-70">{t.time}</div>
                        </td>
                        <td className="px-6 py-4 font-medium">
                          {t.name}
                        </td>
                        <td className="px-6 py-4">
                           <span className={`px-2 py-1 rounded-full text-xs ${
                             t.transaction_type === 'Received from' 
                               ? 'bg-emerald-500/10 text-emerald-400' 
                               : 'bg-rose-500/10 text-rose-400'
                           }`}>
                             {t.transaction_type === 'Received from' ? 'Credit' : 'Debit'}
                           </span>
                        </td>
                        <td className={`px-6 py-4 text-right font-bold ${
                          t.amount > 0 ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                          {t.amount > 0 ? '+' : ''}{formatCurrency(t.amount)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}