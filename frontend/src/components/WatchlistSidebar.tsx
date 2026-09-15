import { NavLink } from "react-router-dom";
import type { Snapshot, WatchlistItem } from "../types";
import { displaySymbol, formatNumber, formatPct, signedClass } from "../utils";
import SearchBox from "./SearchBox";

type Props = {
  items: WatchlistItem[];
  quotes: Record<string, Snapshot>;
  onRefresh: () => void;
  open?: boolean;
};

export default function WatchlistSidebar({ items, quotes, onRefresh, open = false }: Props) {
  return (
    <aside id="watchlist-sidebar" className={`sidebar${open ? " open" : ""}`}>
      <div className="row-between">
        <h3 style={{ margin: "0 0 10px" }}>自选</h3>
      </div>
      <SearchBox onAdded={onRefresh} />
      <div className="stack" style={{ gap: 4 }}>
        {items.length === 0 ? <p className="muted">自选为空。搜索美股代码加入。</p> : null}
        {items.map((item) => {
          const quote = quotes[item.code];
          const chg = quote?.change_rate;
          return (
            <NavLink
              key={item.code}
              to={`/stock/${encodeURIComponent(item.code)}`}
              className={({ isActive }) => `watch-item${isActive ? " active" : ""}`}
            >
              <div>
                <div className="sym">{displaySymbol(item.code)}</div>
                <div className="name">{item.name || item.code}</div>
              </div>
              <div className="watch-quote">
                <div className="sym">{quote?.last_price != null ? formatNumber(quote.last_price) : "—"}</div>
                <div className={`chg ${signedClass(chg ?? null)}`}>
                  {chg == null ? "—" : formatPct(chg, true)}
                </div>
              </div>
            </NavLink>
          );
        })}
      </div>
    </aside>
  );
}
