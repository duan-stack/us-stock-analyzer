import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { HotItem, OverviewResponse, RankItem } from "../types";
import { displaySymbol, formatCompact, formatNumber, formatPct, sessionLine, signedClass } from "../utils";

export default function Overview() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      api
        .overview()
        .then((payload) => {
          if (cancelled) return;
          setData(payload);
          setError("");
        })
        .catch((err) => {
          if (cancelled) return;
          setError(err instanceof Error ? err.message : "总览加载失败");
        });
    };
    load();
    const id = window.setInterval(load, 15000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  if (!data && error) {
    return (
      <div className="card">
        <h3>市场总览</h3>
        <div className="error">{error}</div>
        <p className="muted">未连通 OpenD 时仍可从左侧打开自选标的，但不会展示虚构行情。</p>
      </div>
    );
  }
  if (!data) return <div className="muted">加载市场总览…</div>;

  const usBoard = data.us ?? {
    top_gainers: data.top_gainers,
    top_losers: data.top_losers,
    hot_list: data.hot_list,
  };
  const session = data.us_session;

  return (
    <div className="stack">
      <div className="grid-2">
        <div className="card">
          <h3>美股交易时段</h3>
          <div className="metric">
            <div className="lab">当前状态</div>
            <div className="val">{session?.label || data.market_us_label || data.market_us || "未知"}</div>
          </div>
          <p className="muted">{sessionLine(session)}</p>
          {session?.holiday ? <p className="muted">今日为美股休市日</p> : null}
          {session?.early_close ? <p className="muted">今日提前收盘（13:00 ET）</p> : null}
          <p className="muted">
            {data.opend_connected ? "行情由 FutuOpenD 提供，约 15 秒刷新" : data.error || "请启动 FutuOpenD"}
          </p>
        </div>
        <div className="card">
          <h3>自选覆盖</h3>
          <div className="metric">
            <div className="lab">标的数量</div>
            <div className="val">{data.watchlist.length}</div>
          </div>
          {(error || data.watchlist_error) && <div className="error">{error || data.watchlist_error}</div>}
          <p className="muted">只覆盖美股。搜索 AAPL、NVDA、SPY 即可加入。</p>
        </div>
      </div>
      <div className="card">
        <h3>数据说明</h3>
        <p className="muted">
          行情、K 线与榜单来自富途 OpenD。资讯另行聚合 Yahoo Finance、Google 新闻、新浪财经，富途仅作补充来源之一；某一源失败不会阻断其余来源。
        </p>
      </div>

      <div className="card">
        <h3>自选快照</h3>
        {data.watchlist.length === 0 ? (
          <p className="muted">自选为空。从左侧搜索美股代码加入。</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>代码</th>
                <th>名称</th>
                <th className="num">现价</th>
                <th className="num">涨跌幅</th>
                <th className="num">盘前</th>
                <th className="num">盘后</th>
                <th className="num">成交额</th>
                <th className="num">市值</th>
              </tr>
            </thead>
            <tbody>
              {data.watchlist.map((row) => (
                <tr key={row.code}>
                  <td>
                    <Link to={`/stock/${encodeURIComponent(row.code)}`}>{displaySymbol(row.code)}</Link>
                  </td>
                  <td>{row.name || "—"}</td>
                  <td className="num">{formatNumber(row.last_price)}</td>
                  <td className={`num ${signedClass(row.change_rate)}`}>{formatPct(row.change_rate, true)}</td>
                  <td className={`num ${signedClass(row.pre_change_rate)}`}>
                    {row.pre_price != null ? formatNumber(row.pre_price) : "—"}
                  </td>
                  <td className={`num ${signedClass(row.after_change_rate)}`}>
                    {row.after_price != null ? formatNumber(row.after_price) : "—"}
                  </td>
                  <td className="num">{formatCompact(row.turnover)}</td>
                  <td className="num">{formatCompact(row.total_market_val)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <MarketSection board={usBoard} />
    </div>
  );
}

function MarketSection({ board }: { board: NonNullable<OverviewResponse["us"]> }) {
  const hasRanks = board.top_gainers.available || board.top_losers.available;
  const hasHot = board.hot_list.available;
  if (!hasRanks && !hasHot) {
    return (
      <div className="card">
        <h3>美股榜单</h3>
        <p className="muted">榜单暂不可用（无权限或接口未返回）。</p>
      </div>
    );
  }
  return (
    <div className="stack">
      {hasRanks && (
        <div className="grid-2">
          {board.top_gainers.available && (
            <div className="card">
              <h3>今日领涨</h3>
              <RankTable items={board.top_gainers.items} />
            </div>
          )}
          {board.top_losers.available && (
            <div className="card">
              <h3>今日领跌</h3>
              <RankTable items={board.top_losers.items} />
            </div>
          )}
        </div>
      )}
      {hasHot && (
        <div className="card">
          <h3>热议</h3>
          <HotTable items={board.hot_list.items} />
        </div>
      )}
    </div>
  );
}

function RankTable({ items }: { items: RankItem[] }) {
  if (!items.length) return <p className="muted">暂无数据</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>代码</th>
          <th>名称</th>
          <th className="num">现价</th>
          <th className="num">涨跌幅</th>
        </tr>
      </thead>
      <tbody>
        {items.map((row, idx) => (
          <tr key={`${row.code}-${idx}`}>
            <td>
              {row.code ? <Link to={`/stock/${encodeURIComponent(row.code)}`}>{displaySymbol(row.code)}</Link> : "—"}
            </td>
            <td>{row.name || "—"}</td>
            <td className="num">{formatNumber(row.last_price)}</td>
            <td className={`num ${signedClass(row.change_rate)}`}>{formatPct(row.change_rate, true)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function HotTable({ items }: { items: HotItem[] }) {
  if (!items.length) return <p className="muted">暂无数据</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>代码</th>
          <th>名称</th>
          <th className="num">热度</th>
          <th>标题</th>
        </tr>
      </thead>
      <tbody>
        {items.map((row, idx) => (
          <tr key={`${row.code}-${idx}`}>
            <td>
              {row.code ? (
                <Link to={`/stock/${encodeURIComponent(row.code)}`}>{displaySymbol(row.code)}</Link>
              ) : (
                "—"
              )}
            </td>
            <td>{row.name || "—"}</td>
            <td className="num">{formatNumber(row.average_heat)}</td>
            <td>
              {row.news_url ? (
                <a href={row.news_url} target="_blank" rel="noreferrer">
                  {row.news_title || row.news_url}
                </a>
              ) : (
                row.news_title || "—"
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
