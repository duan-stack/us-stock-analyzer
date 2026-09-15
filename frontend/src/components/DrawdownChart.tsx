import { createChart } from "lightweight-charts";
import { useEffect, useRef } from "react";
import type { DrawdownPoint } from "../types";

export default function DrawdownChart({ series }: { series: DrawdownPoint[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const host = ref.current;
    if (!host) return;
    host.replaceChildren();
    const chart = createChart(host, {
      width: host.clientWidth,
      height: host.clientHeight || 220,
      layout: { background: { color: "#ffffff" }, textColor: "#667085" },
      grid: { vertLines: { color: "#eef1f5" }, horzLines: { color: "#eef1f5" } },
      rightPriceScale: { borderColor: "#e6ebf1" },
      timeScale: { borderColor: "#e6ebf1" },
    });
    const area = chart.addAreaSeries({
      lineColor: "#dc2626",
      topColor: "rgba(220,38,38,0.06)",
      bottomColor: "rgba(220,38,38,0.28)",
      lineWidth: 1,
      priceFormat: { type: "percent" },
    });
    area.setData(
      series
        .filter((p) => p.time)
        .map((p) => ({
          time: String(p.time).slice(0, 10),
          value: p.drawdown * 100,
        })),
    );
    chart.timeScale().fitContent();
    const applySize = () => {
      chart.applyOptions({ width: host.clientWidth, height: host.clientHeight || 220 });
    };
    const observer = new ResizeObserver(applySize);
    observer.observe(host);
    window.addEventListener("resize", applySize);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", applySize);
      chart.remove();
    };
  }, [series]);

  if (!series.length) {
    return <div className="muted">暂无回撤序列。</div>;
  }

  return <div ref={ref} className="drawdown-host" />;
}
