import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api";
import DrawdownChart from "../components/DrawdownChart";
import KlineChart from "../components/KlineChart";
import NewsList from "../components/NewsList";
import ReportPanel from "../components/ReportPanel";
import type { DrawdownMetrics, KlineBar, NewsItem, NewsSourceStatus, OptionalBlock, Snapshot } from "../types";
import { dateOnly, displaySymbol, formatCompact, formatNumber, formatPct, signedClass } from "../utils";

const PERIODS = [
  { id: "K_5M", label: "5分" },
  { id: "K_15M", label: "15分" },
  { id: "K_60M", label: "60分" },
  { id: "K_DAY", label: "日" },
  { id: "K_WEEK", label: "周" },
];

export default function StockDetail() {
  const { code: raw } = useParams();
  const code = decodeURIComponent(raw || "");
  const [ktype, setKtype] = useState("K_DAY");
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [bars, setBars] = useState<KlineBar[]>([]);
  const [klineLoading, setKlineLoading] = useState(false);
  const [klineError, setKlineError] = useState("");
  const [dd, setDd] = useState<DrawdownMetrics | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [newsSources, setNewsSources] = useState<NewsSourceStatus[]>([]);
  const [plates, setPlates] = useState<OptionalBlock<{ plate_name?: string; plate_type?: string }>>({
    available: false,
    items: [],
  });
  const [flow, setFlow] = useState<OptionalBlock<{ time?: string; in_flow?: number }>>({ available: false, items: [] });
  const [profile, setProfile] = useState<OptionalBlock<{ name?: string; value?: string }>>({ available: false, items: [] });
  const [errors, setErrors] = useState<string[]>([]);

  useEffect(() => {
    if (!code) return;
    setErrors([]);
    setSnap(null);
    setBars([]);
    setDd(null);
    setNews([]);
    setNewsSources([]);
    const loadSnap = () =>
      api
        .snapshot(code)
        .then(setSnap)
        .catch((err) => setErrors((xs) => [...xs, err instanceof Error ? err.message : "快照失败"]));
    void loadSnap();
    const snapTimer = window.setInterval(() => {
      api.snapshot(code).then(setSnap).catch(() => undefined);
    }, 15000);
    api
      .drawdown(code)
      .then(setDd)
      .catch((err) => setErrors((xs) => [...xs, err instanceof Error ? err.message : "回撤失败"]));
    api
      .news(code)
      .then((res) => {
        setNews(res.items || []);
        setNewsSources(res.sources || []);
      })
      .catch((err) => setErrors((xs) => [...xs, err instanceof Error ? err.message : "资讯失败"]));
    api.plates(code).then(setPlates).catch(() => setPlates({ available: false, items: [] }));
    api.capitalFlow(code).then(setFlow).catch(() => setFlow({ available: false, items: [] }));
    api.profile(code).then(setProfile).catch(() => setProfile({ available: false, items: [] }));
    return () => window.clearInterval(snapTimer);
  }, [code]);

  useEffect(() => {
    if (!code) return;
    setKlineLoading(true);
    setKlineError("");
    api
      .kline(code, ktype)
      .then((res) => setBars(res.bars || []))
      .catch((err) => {
        setBars([]);
        setKlineError(err instanceof Error ? err.message : "K线失败");
      })
      .finally(() => setKlineLoading(false));
  }, [code, ktype]);

  const chg = snap?.change_rate;

  return (
    <div className="stack">
      <div className="card">
        <div className="quote-head">
          <div>
            <div className="muted">{code}</div>
            <h2 style={{ margin: "4px 0 0" }}>
              {displaySymbol(code)} {snap?.name || ""}
            </h2>
            {snap?.update_time ? <div className="muted">{snap.update_time}</div> : null}
          </div>
          <div>
            <div className={`price ${signedClass(chg)}`}>{formatNumber(snap?.last_price)}</div>
            <div className={signedClass(chg)}>
              {formatPct(chg, true)} {snap?.change_val != null ? `(${formatNumber(snap.change_val)})` : ""}
            </div>
          </div>
        </div>
        <div className="metrics" style={{ marginTop: 14 }}>
          <div className="metric">
            <div className="lab">开 / 高 / 低</div>
            <div className="val" style={{ fontSize: 14 }}>
              {formatNumber(snap?.open_price)} / {formatNumber(snap?.high_price)} / {formatNumber(snap?.low_price)}
            </div>
          </div>
          <div className="metric">
            <div className="lab">盘前</div>
            <div className={`val ${signedClass(snap?.pre_change_rate)}`} style={{ fontSize: 16 }}>
              {snap?.pre_price != null ? formatNumber(snap.pre_price) : "—"}
              {snap?.pre_change_rate != null ? ` ${formatPct(snap.pre_change_rate, true)}` : ""}
            </div>
          </div>
          <div className="metric">
            <div className="lab">盘后</div>
            <div className={`val ${signedClass(snap?.after_change_rate)}`} style={{ fontSize: 16 }}>
              {snap?.after_price != null ? formatNumber(snap.after_price) : "—"}
              {snap?.after_change_rate != null ? ` ${formatPct(snap.after_change_rate, true)}` : ""}
            </div>
          </div>
          <div className="metric">
            <div className="lab">成交额 / 量</div>
            <div className="val" style={{ fontSize: 16 }}>
              {formatCompact(snap?.turnover)} / {formatCompact(snap?.volume)}
            </div>
          </div>
          <div className="metric">
            <div className="lab">市值</div>
            <div className="val">{formatCompact(snap?.total_market_val)}</div>
          </div>
          <div className="metric">
            <div className="lab">PE / PB</div>
            <div className="val" style={{ fontSize: 16 }}>
              {formatNumber(snap?.pe_ratio)} / {formatNumber(snap?.pb_ratio)}
            </div>
          </div>
          <div className="metric">
            <div className="lab">52周</div>
            <div className="val" style={{ fontSize: 14 }}>
              {formatNumber(snap?.lowest52weeks_price)} - {formatNumber(snap?.highest52weeks_price)}
            </div>
          </div>
        </div>
        {[...new Set(errors)].map((msg) => (
          <div className="error" key={msg} style={{ marginTop: 8 }}>
            {msg}
          </div>
        ))}
      </div>

      <div className="detail-grid">
        <div className="stack">
          <div className="card">
            <div className="row-between">
              <h3 style={{ margin: 0 }}>K 线</h3>
              <div className="tabs">
                {PERIODS.map((p) => (
                  <button key={p.id} className={`btn ${ktype === p.id ? "active" : ""}`} onClick={() => setKtype(p.id)}>
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <p className="muted">蜡烛 + 成交量 + MA5/10/20，前复权。切换周期会重新拉取。</p>
            {klineError ? <div className="error">{klineError}</div> : null}
            {klineLoading ? <p className="muted">加载 K 线…</p> : <KlineChart bars={bars} ktype={ktype} />}
          </div>

          <div className="card">
            <h3>价格回撤</h3>
            <div className="metrics">
              <div className="metric">
                <div className="lab">当前回撤</div>
                <div className={`val ${signedClass(dd?.current_drawdown)}`}>{formatPct(dd?.current_drawdown)}</div>
              </div>
              <div className="metric">
                <div className="lab">最大回撤</div>
                <div className="val down">{formatPct(dd?.max_drawdown)}</div>
              </div>
              <div className="metric">
                <div className="lab">水下天数</div>
                <div className="val">{dd?.underwater_days ?? "—"}</div>
              </div>
              <div className="metric">
                <div className="lab">低点反弹</div>
                <div className={`val ${signedClass(dd?.rebound_from_trough)}`}>{formatPct(dd?.rebound_from_trough)}</div>
              </div>
            </div>
            <p className="muted">
              最大回撤区间 {dateOnly(dd?.max_drawdown_start)} → {dateOnly(dd?.max_drawdown_end)} · 区间收益{" "}
              {formatPct(dd?.period_return)}
            </p>
            <DrawdownChart series={dd?.series || []} />
          </div>

          {plates.available && plates.items.length > 0 && (
            <div className="card">
              <h3>所属板块</h3>
              <div className="chips">
                {plates.items.map((p) => (
                  <span className="chip" key={`${p.plate_name}-${p.plate_type}`}>
                    {p.plate_name}
                    {p.plate_type ? ` · ${p.plate_type}` : ""}
                  </span>
                ))}
              </div>
            </div>
          )}

          {flow.available && flow.items.length > 0 && (
            <div className="card">
              <h3>资金流向</h3>
              <table>
                <thead>
                  <tr>
                    <th>时间</th>
                    <th className="num">净流入</th>
                  </tr>
                </thead>
                <tbody>
                  {flow.items.slice(-12).map((row, idx) => (
                    <tr key={`${row.time}-${idx}`}>
                      <td>{row.time || "—"}</td>
                      <td className={`num ${signedClass(row.in_flow)}`}>{formatCompact(row.in_flow)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {profile.available && profile.items.length > 0 && (
            <div className="card">
              <h3>公司简介</h3>
              {profile.items.slice(0, 12).map((row, idx) => (
                <p key={`${row.name}-${idx}`}>
                  <span className="muted">{row.name}：</span>
                  {row.value}
                </p>
              ))}
            </div>
          )}
        </div>

        <div className="stack">
          <div className="card">
            <h3>资讯</h3>
            <p className="muted">聚合 Yahoo Finance、Google 新闻、新浪财经与富途，不依赖单一来源。</p>
            <NewsList items={news} sources={newsSources} />
          </div>
          <ReportPanel code={code} />
        </div>
      </div>
    </div>
  );
}
