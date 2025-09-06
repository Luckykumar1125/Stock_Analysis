// Inside your AIInsights.tsx or a new component
import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

// Define a type for the data coming from the backend
interface BackendInsight {
  market_sentiment: string;
  market_sentiment_description: string;
  volatility_alert: string;
  volatility_alert_description: string;
  top_recommendation: string;
  top_recommendation_description: string;
  risk_assessment: string;
  risk_assessment_description: string;
}

// Define the Insight type used in this component
interface Insight {
  type: string;
  status: string;
  description: string;
  statusColor: string;
}

// Convert backend data to the format your component expects
const mapToInsights = (data: BackendInsight): Insight[] => {
  const getStatusColor = (status: string) => {
    // Map backend statuses to colors
    if (status.includes('Bullish') || status.includes('Invest')) return 'success';
    if (status.includes('Moderate') || status.includes('Medium')) return 'warning';
    return 'destructive';
  };

  return [
    {
      type: 'Market Sentiment',
      status: `${data.market_sentiment} 📈`,
      description: data.market_sentiment_description,
      statusColor: getStatusColor(data.market_sentiment),
    },
    {
      type: 'Volatility Alert',
      status: `${data.volatility_alert} ⚡`,
      description: data.volatility_alert_description,
      statusColor: getStatusColor(data.volatility_alert),
    },
    {
      type: 'Top Recommendation',
      status: `${data.top_recommendation}`,
      description: data.top_recommendation_description,
      statusColor: getStatusColor(data.top_recommendation),
    },
    {
      type: 'Risk Assessment',
      status: `${data.risk_assessment} 🎯`,
      description: data.risk_assessment_description,
      statusColor: getStatusColor(data.risk_assessment),
    },
  ];
};

export const AIInsights = () => {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const response = await fetch('http://127.0.0.1:8000/market-insights');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const backendData: BackendInsight = await response.json();
        const mappedInsights = mapToInsights(backendData);
        setInsights(mappedInsights);
      } catch (e) {
        if (e instanceof Error) {
            setError(e.message);
        } else {
            setError("An unknown error occurred.");
        }
      } finally {
        setIsLoading(false);
      }
    };
    fetchInsights();
  }, []);

  const getStatusBadgeClass = (color: string) => {
    switch (color) {
      case 'success':
        return 'bg-success/20 text-success border-success/30';
      case 'warning':
        return 'bg-warning/20 text-warning border-warning/30';
      case 'destructive':
        return 'bg-destructive/20 text-destructive border-destructive/30';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  if (isLoading) {
    return (
      <Card className="glass-card border-card-border">
        <CardHeader><CardTitle>Loading AI Insights... ⏳</CardTitle></CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="glass-card border-card-border">
        <CardHeader><CardTitle>Error Fetching Insights ❌</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-destructive">{error}</p></CardContent>
      </Card>
    );
  }

  return (
    <Card className="glass-card border-card-border">
      <CardHeader>
        <CardTitle className="flex items-center">
          🤖 AI Market Insights
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {insights.map((insight, index) => (
          <div
            key={insight.type}
            className={`p-4 rounded-lg bg-accent/30 border border-accent animate-fade-in`}
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold">{insight.type}:</span>
              <span className={`px-3 py-1 rounded-full text-sm border ${getStatusBadgeClass(insight.statusColor)}`}>
                {insight.status}
              </span>
            </div>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {insight.description}
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};