// import { useEffect, useState } from "react";
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// import {
//   LineChart,
//   Line,
//   XAxis,
//   YAxis,
//   Tooltip,
//   ResponsiveContainer,
//   CartesianGrid,
// } from "recharts";

// // Types
// interface ChartDataPoint {
//   timestamp: number;
//   open: number;
//   high: number;
//   low: number;
//   close: number;
//   volume: number;
// }

// interface IndexChart {
//   symbol: string;
//   name: string;
//   data: ChartDataPoint[];
// }

// export const ChartContainer = () => {
//   const [indices, setIndices] = useState<IndexChart[]>([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     const fetchCharts = async () => {
//       try {
//         const res = await fetch("http://127.0.0.1:8000/live-indices");
//         const raw = await res.json();

//         // Convert dict → array
//         const formatted: IndexChart[] = Object.entries(raw).map(
//           ([symbol, details]: [string, any]) => ({
//             symbol,
//             name: details.name,
//             data: details.data,
//           })
//         );

//         setIndices(formatted);
//       } catch (err) {
//         console.error("Error fetching charts:", err);
//       } finally {
//         setLoading(false);
//       }
//     };

//     fetchCharts();
//   }, []);

//   if (loading) {
//     return (
//       <Card className="glass-card border-card-border mb-8">
//         <CardHeader>
//           <CardTitle>Loading Real-Time Market Analysis...</CardTitle>
//         </CardHeader>
//         <CardContent>
//           <div className="h-64 flex items-center justify-center">
//             <div className="text-muted-foreground">Fetching live chart data...</div>
//           </div>
//         </CardContent>
//       </Card>
//     );
//   }

//   return (
//     <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
//       {indices.map((index, idx) => {
//         const firstDate =
//           index.data.length > 0
//             ? new Date(index.data[0].timestamp * 1000).toLocaleDateString(
//                 "en-IN",
//                 { day: "2-digit", month: "short", year: "numeric" }
//               )
//             : "";

//         return (
//           <Card key={idx} className="glass-card border-card-border relative">
//             <CardHeader>
//               <CardTitle className="text-base">
//                 {index.name} ({index.symbol})
//               </CardTitle>
//             </CardHeader>
//             <CardContent>
//               {/* Date at top-left */}
//               {firstDate && (
//                 <div className="absolute top-12 left-6 text-xs text-muted-foreground">
//                   {firstDate}
//                 </div>
//               )}
//               <ResponsiveContainer width="100%" height={200}>
//                 <LineChart data={index.data}>
//                   <CartesianGrid strokeDasharray="3 3" />
//                   <XAxis
//                     dataKey="timestamp"
//                     tickFormatter={(ts) =>
//                       new Date(ts * 1000).toLocaleTimeString("en-IN", {
//                         hour: "2-digit",
//                         minute: "2-digit",
//                       })
//                     }
//                   />
//                   <YAxis domain={["auto", "auto"]} />
//                   <Tooltip
//                     labelFormatter={(ts) =>
//                       new Date(ts * 1000).toLocaleString("en-IN", {
//                         day: "2-digit",
//                         month: "short",
//                         hour: "2-digit",
//                         minute: "2-digit",
//                       })
//                     }
//                   />
//                   <Line
//                     type="monotone"
//                     dataKey="close"
//                     stroke="#3b82f6"
//                     strokeWidth={2}
//                     dot={false}
//                   />
//                 </LineChart>
//               </ResponsiveContainer>
//             </CardContent>
//           </Card>
//         );
//       })}
//     </div>
//   );
// };

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
// --- REMOVED ---
// import {
//   LineChart,
//   Line,
//   XAxis,
//   YAxis,
//   Tooltip,
//   ResponsiveContainer,
//   CartesianGrid,
// } from "recharts";

// +++ ADDED +++
// Import your new chart component (adjust the path if needed)
import { StockChart } from "@/components/StockChart";

// Types (These remain the same)
interface ChartDataPoint {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface IndexChart {
  symbol: string;
  name: string;
  data: ChartDataPoint[];
}

export const ChartContainer = () => {
  const [indices, setIndices] = useState<IndexChart[]>([]);
  const [loading, setLoading] = useState(true);

  // This useEffect hook for fetching data remains exactly the same
  useEffect(() => {
    const fetchCharts = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/live-indices");
        const raw = await res.json();

        // Convert dict → array
        const formatted: IndexChart[] = Object.entries(raw).map(
          ([symbol, details]: [string, any]) => ({
            symbol,
            name: details.name,
            data: details.data,
          })
        );

        setIndices(formatted);
      } catch (err) {
        console.error("Error fetching charts:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchCharts();
  }, []);

  // The loading state card also remains the same
  if (loading) {
    return (
      <Card className="glass-card border-card-border mb-8">
        <CardHeader>
          <CardTitle>Loading Real-Time Market Analysis...</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center">
            <div className="text-muted-foreground">Fetching live chart data...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // This is the main render block that changes
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {indices.map((index, idx) => {
        const firstDate =
          index.data.length > 0
            ? new Date(index.data[0].timestamp * 1000).toLocaleDateString(
                "en-IN",
                { day: "2-digit", month: "short", year: "numeric" }
              )
            : "";

        return (
          <Card key={idx} className="glass-card border-card-border relative">
            <CardHeader>
              <CardTitle className="text-base">
                {index.name} ({index.symbol})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {/* Date at top-left */}
              {firstDate && (
                <div className="absolute top-12 left-6 text-xs text-muted-foreground">
                  {firstDate}
                </div>
              )}

              {/* === THIS IS THE REPLACEMENT === */}
              {/* We removed the <ResponsiveContainer> and <LineChart> ... */}
              {/* ... and replaced it with our new <StockChart> */}

              {index.data.length > 0 ? (
                <StockChart data={index.data} />
              ) : (
                <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                  No data available for this index.
                </div>
              )}
              {/* === END OF REPLACEMENT === */}
              
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
};