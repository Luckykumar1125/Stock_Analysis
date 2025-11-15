import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  CandlestickSeries,
  HistogramSeries,
  // === ADD THIS TYPE ===
  UTCTimestamp,
} from "lightweight-charts";

// This is the same type from your ChartContainer
interface ChartDataPoint {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface StockChartProps {
  data: ChartDataPoint[];
}

export const StockChart = ({ data }: StockChartProps) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) {
      return;
    }

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "rgba(255, 255, 255, 0.7)",
      },
      grid: {
        vertLines: { color: "rgba(197, 203, 206, 0.2)" },
        horzLines: { color: "rgba(197, 203, 206, 0.2)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      timeScale: {
        borderColor: "rgba(197, 203, 206, 0.4)",
      },
    });

    // Format data for Lightweight Charts
    const candleStickData = data.map((d) => ({
      // === CAST THE TYPE HERE ===
      time: d.timestamp as UTCTimestamp,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }));

    const volumeData = data.map((d) => ({
      // === AND CAST IT HERE ===
      time: d.timestamp as UTCTimestamp,
      value: d.volume,
    }));

    // Add Candlestick Series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderDownColor: "#ef5350",
      borderUpColor: "#26a69a",
      wickDownColor: "#ef5350",
      wickUpColor: "#26a69a",
    });
    // This assignment will now work
    candleSeries.setData(candleStickData);

    // Add Volume Series (Histogram)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: "#3b82f6",
      priceFormat: {
        type: "volume",
      },
      priceScaleId: "volume_scale",
    });
    // This assignment will also work
    volumeSeries.setData(volumeData);

    chart.priceScale("volume_scale").applyOptions({
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.resize(chartContainerRef.current.clientWidth, 300);
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
};