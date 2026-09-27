import { useOutletContext } from "react-router-dom";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { HealthResponse, Snapshot, WatchlistItem } from "../types";
import { displaySymbol, formatNumber, formatPct, signedClass } from "../utils";

type Ctx = {
  watchlist: WatchlistItem[];
  quotes: Record<string, Snapshot>;
  health: HealthResponse | null;
  refresh: () => Promise<void>;
};

export default function WatchlistPage() {
  const { watchlist, quotes, refresh } = useOutletContext<Ctx>();

  async function remove(code: string) {
    await api.removeWatchlist(code);
    await refresh();
  }

  async function togglePin(code: string, pinned?: boolean) {
    await api.pinWatchlist(code, !pinned);
    await refresh();
  }

  async function move(code: string, direction: -1 | 1) {
    const codes = watchlist.map((item) => item.code);
    const idx = codes.indexOf(code);
    const next = idx + direction;
    if (idx < 0 || next < 0 || next >= codes.length) return;
    const swapped = [...codes];
    [swapped[idx], swapped[next]] = [swapped[next], swapped[idx]];
    await api.reorderWatchlist(swapped);
    await refresh();
  }

  return (
    <div className="card">
      <h2>自选股</h2>
      <p className="muted">本地保存美股自选。可置顶与调整顺序；左侧搜索 AAPL、NVDA、SPY 即可加入。</p>
      {watchlist.length === 0 ? (
        <p className="muted">自选为空。从左侧搜索美股代码加入。</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th className="num">现价</th>
              <th className="num">涨跌幅</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {watchlist.map((item, index) => {
              const q = quotes[item.code];
              return (
                <tr key={item.code}>
                  <td>
                    <Link to={`/stock/${encodeURIComponent(item.code)}`}>{displaySymbol(item.code)}</Link>
                    <div className="muted">
                      {item.code}
                      {item.pinned ? " · 置顶" : ""}
                    </div>
                  </td>
                  <td>{item.name}</td>
                  <td className="num">{formatNumber(q?.last_price)}</td>
                  <td className={`num ${signedClass(q?.change_rate)}`}>{formatPct(q?.change_rate, true)}</td>
                  <td>
                    <div className="row-actions">
                      <button className="btn ghost" onClick={() => void togglePin(item.code, item.pinned)}>
                        {item.pinned ? "取消置顶" : "置顶"}
                      </button>
                      <button className="btn ghost" disabled={index === 0} onClick={() => void move(item.code, -1)}>
                        上移
                      </button>
                      <button
                        className="btn ghost"
                        disabled={index === watchlist.length - 1}
                        onClick={() => void move(item.code, 1)}
                      >
                        下移
                      </button>
                      <button className="btn ghost" onClick={() => void remove(item.code)}>
                        移除
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
