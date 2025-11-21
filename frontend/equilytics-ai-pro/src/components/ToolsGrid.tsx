import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import SentimentModal from "@/components/SentimentModal";
import StockScreener from "@/components/StockScreener";
import PortfolioAnalyzer from "./PortfolioAnalyzer";
import BalanceSheetAnalyzer from "./BalanceSheetAnalyzer"; // <--- Imported here
import StockDashboard from "./PricePredictions";

interface Tool {
  id: string;
  icon: string;
  title: string;
  description: string;
  action: string;
}

export const ToolsGrid = () => {
  const [selectedTool, setSelectedTool] = useState<string | null>(null);

  const tools: Tool[] = [
    {
      id: "screener",
      icon: "🔍",
      title: "Stock Screener",
      description:
        "Advanced filtering tools to find stocks matching your criteria with AI-powered recommendations and real-time analysis.",
      action: "Launch Screener",
    },
    {
      id: "portfolio",
      icon: "📊",
      title: "Portfolio Analyzer",
      description:
        "Comprehensive portfolio analysis with risk assessment, performance metrics, and optimization suggestions.",
      action: "Analyze Portfolio",
    },
    {
      id: "balance",
      icon: "📋",
      title: "Balance Sheet Analyzer",
      description:
        "Simplified financial statement analysis with AI-powered insights, health scores, and trend analysis.",
      action: "Analyze Financials",
    },
    {
      id: "sentiment",
      icon: "💬",
      title: "Sentiment Analysis",
      description:
        "Real-time social media and news sentiment analysis for market-moving insights and trend predictions.",
      action: "View Sentiment",
    },
    {
      id: "predictions",
      icon: "🔮",
      title: "Price Predictions",
      description:
        "AI-powered stock price forecasting using advanced machine learning models and technical indicators.",
      action: "Get Predictions",
    },
    {
      id: "risk",
      icon: "⚠️",
      title: "Risk Calculator",
      description:
        "Personalized risk assessment based on your profile, investment goals, and current market conditions.",
      action: "Calculate Risk",
    },
  ];

  // Helper to get the data for the currently selected tool
  const activeToolData = tools.find((t) => t.id === selectedTool);

  return (
    <div className="mb-8">
      <h2 className="text-3xl font-bold mb-8 text-center">
        <span className="gradient-primary bg-clip-text text-transparent">
          Investment Tools & Analytics
        </span>
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tools.map((tool, index) => (
          <Card
            key={tool.id}
            className="glass-card border-card-border hover:shadow-glow transition-all duration-500 cursor-pointer group animate-slide-up"
            style={{ animationDelay: `${index * 0.1}s` }}
            onClick={() => setSelectedTool(tool.id)}
          >
            <CardContent className="p-6 text-center">
              <div className="text-4xl mb-4 group-hover:animate-float transition-all duration-300">
                {tool.icon}
              </div>
              <h3 className="text-xl font-bold mb-3 group-hover:text-primary transition-colors">
                {tool.title}
              </h3>
              <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
                {tool.description}
              </p>
              <Button
                className="w-full gradient-primary shadow-primary hover:shadow-glow transition-all duration-300"
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedTool(tool.id);
                }}
              >
                {tool.action}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* --- Modals Section --- */}

      {/* 1. Sentiment Modal */}
      {selectedTool === "sentiment" && (
        <SentimentModal onClose={() => setSelectedTool(null)} />
      )}

      {/* 2. Stock Screener Modal */}
      {selectedTool === "screener" && activeToolData && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-background border border-border/50 rounded-xl shadow-2xl w-full max-w-7xl max-h-[90vh] overflow-y-auto p-6 relative animate-in fade-in zoom-in-95 duration-200 custom-scrollbar">
            <button
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors font-bold text-xl z-10"
              onClick={() => setSelectedTool(null)}
            >
              ✕
            </button>
            
            <StockScreener 
              id={activeToolData.id}
              icon={activeToolData.icon}
              title={activeToolData.title}
              description={activeToolData.description}
              action={activeToolData.action}
            />
          </div>
        </div>
      )}

      {/* 3. Portfolio Analyzer Modal */}
      {selectedTool === "portfolio" && activeToolData && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-background border border-border/50 rounded-xl shadow-2xl w-full max-w-7xl max-h-[90vh] overflow-y-auto p-6 relative animate-in fade-in zoom-in-95 duration-200 custom-scrollbar">
            <button
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors font-bold text-xl z-10"
              onClick={() => setSelectedTool(null)}
            >
              ✕
            </button>
            
            <PortfolioAnalyzer />
          </div>
        </div>
      )}

      {/* 4. Balance Sheet Analyzer Modal (NEW) */}
      {selectedTool === "balance" && activeToolData && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          <div className="bg-background border border-border/50 rounded-xl shadow-2xl w-full max-w-7xl max-h-[90vh] overflow-y-auto p-6 relative animate-in fade-in zoom-in-95 duration-200 custom-scrollbar">
            <button
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors font-bold text-xl z-10"
              onClick={() => setSelectedTool(null)}
            >
              ✕
            </button>
            
            <BalanceSheetAnalyzer />
          </div>
        </div>
      )}
      {/* 5. Price Predictions Modal (NEW) */}
      {selectedTool === "predictions" && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex justify-center items-center z-50 p-4">
          {/* Note: We use max-w-full or max-w-[90vw] here to give the dashboard enough room,
             and removed p-6 padding from the container because StockDashboard has its own padding.
          */}
          <div className="bg-background border border-border/50 rounded-xl shadow-2xl w-full max-w-[95vw] max-h-[95vh] overflow-y-auto relative animate-in fade-in zoom-in-95 duration-200 custom-scrollbar">
            
            {/* Close Button */}
            <button
              className="absolute top-6 right-6 text-muted-foreground hover:text-foreground transition-colors font-bold text-xl z-10 bg-background/50 px-2 rounded-full"
              onClick={() => setSelectedTool(null)}
            >
              ✕
            </button>
            
            {/* Render the Component */}
            <StockDashboard />
          </div>
        </div>
      )}
    </div>
  );
};