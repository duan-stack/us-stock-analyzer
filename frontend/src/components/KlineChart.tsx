import { createChart, UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { KlineBar } from "../types";

function toTime(raw: string, intraday: boolean): UTCTimestamp | string {
  const text = raw.replace("T", " ");
  if (!intraday) return text.slice(0, 10);
  const normalized = text.includes("Z") ? text : `${text.replace(" ", "T")}Z`;
  const ms = Date.parse(normalized);
  if (Number.isNaN(ms)) return text.slice(0, 10);
  return Math.floor(ms / 1000) as UTCTimestamp;
}

function sma(values: { time: UTCTimestamp | string; value: number }[], window: number) {
  return values
    .map((_, i) => {
      if (i + 1 < window) return null;
      const slice = values.slice(i + 1 - window, i + 1);
      const avg = slice.reduce((sum, point) => sum + point.value, 0) / window;
      return { time: values[i].time, value: avg };
    })
    .filter((x): x is { time: UTCTimestamp | string; value: number } => x !== null);
}

export default function KlineChart({ bars, ktype }: { bars: KlineBar[]; ktype: string }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = ref.current;
    if (!host) return;
    const chart = createChart(host, {
      width: host.clientWidth,
      height: host.clientHeight || 420,
      layout: { background: { color: "#ffffff" }, textColor: "#667085" },
      grid: { vertLines: { color: "#eef1f5" }, horzLines: { color: "#eef1f5" } },
      rightPriceScale: { borderColor: "#e6ebf1" },
      timeScale: {
        borderColor: "#e6ebf1",
        timeVisible: !["K_DAY", "K_WEEK", "K_MON"].includes(ktype),
        secondsVisible: false,
      },
    });
    const candle = chart.addCandlestickSeries({
      upColor: "#15803d",
      downColor: "#dc2626",
      borderVisible: false,
      wickUpColor: "#15803d",
      wickDownColor: "#dc2626",
    });
    const vol = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "vol",
    });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    const ma5 = chart.addLineSeries({ color: "#d97706", lineWidth: 1, priceLineVisible: false });
    const ma10 = chart.addLineSeries({ color: "#2563eb", lineWidth: 1, priceLineVisible: false });
    const ma20 = chart.addLineSeries({ color: "#7c3aed", lineWidth: 1, priceLineVisible: false });

    const intraday = !["K_DAY", "K_WEEK", "K_MON"].includes(ktype);
    const candleData = bars
      .filter((b) => b.open != null && b.high != null && b.low != null && b.close != null && b.time)
      .map((b) => ({
        time: toTime(b.time, intraday),
        open: Number(b.open),
        high: Number(b.high),
        low: Number(b.low),
        close: Number(b.close),
      }));
    const volData = bars
      .filter((b) => b.volume != null && b.close != null && b.open != null && b.time)
      .map((b) => ({
        time: toTime(b.time, intraday),
        value: Number(b.volume),
        color: Number(b.close) >= Number(b.open) ? "rgba(21,128,61,0.35)" : "rgba(220,38,38,0.35)",
      }));
    const closes = candleData.map((d) => ({ time: d.time, value: d.close }));
    candle.setData(candleData);
    vol.setData(volData);
    ma5.setData(sma(closes, 5));
    ma10.setData(sma(closes, 10));
    ma20.setData(sma(closes, 20));
    chart.timeScale().fitContent();

    const applySize = () => {
      chart.applyOptions({ width: host.clientWidth, height: host.clientHeight || 420 });
    };
    const observer = new ResizeObserver(applySize);
    observer.observe(host);
    window.addEventListener("resize", applySize);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", applySize);
      chart.remove();
    };
  }, [bars, ktype]);

  if (!bars.length) {
    return <div className="muted">暂无 K 线。请确认 OpenD 已连接且账号有美股行情权限。</div>;
  }

  return <div ref={ref} className="kline-host" />;
}
