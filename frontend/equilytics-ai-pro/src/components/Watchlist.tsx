import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface Stock {
  symbol: string;
  name: string;
  price: string;
  change: string;
  isPositive: boolean;
}

export const Watchlist = () => {
  const stocks: Stock[] = [
    { symbol: 'AAPL', name: 'Apple Inc.', price: '$178.45', change: '+2.34%', isPositive: true },
    { symbol: 'TSLA', name: 'Tesla, Inc.', price: '$267.89', change: '-1.67%', isPositive: false },
    { symbol: 'NVDA', name: 'NVIDIA Corp.', price: '$456.12', change: '+4.21%', isPositive: true },
    { symbol: 'MSFT', name: 'Microsoft Corp.', price: '$412.33', change: '+1.89%', isPositive: true },
  ];

  return (
    <Card className="glass-card border-card-border">
      <CardHeader>
        <CardTitle className="flex items-center">
          📋 Your Watchlist
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {stocks.map((stock, index) => (
            <div
              key={stock.symbol}
              className={`flex justify-between items-center p-3 rounded-lg bg-accent/20 border border-accent hover:bg-accent/30 transition-all duration-300 animate-fade-in cursor-pointer`}
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              <div>
                <div className="font-bold text-primary">{stock.symbol}</div>
                <div className="text-xs text-muted-foreground">{stock.name}</div>
              </div>
              <div className="text-right">
                <div className="font-semibold">{stock.price}</div>
                <div className={`text-xs ${
                  stock.isPositive ? 'text-success' : 'text-destructive'
                }`}>
                  {stock.change}
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
};