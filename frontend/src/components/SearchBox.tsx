import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import type { SearchItem } from "../types";
import { displaySymbol } from "../utils";

export default function SearchBox({ onAdded }: { onAdded?: () => void }) {
  const [q, setQ] = useState("");
  const [items, setItems] = useState<SearchItem[]>([]);
  const [error, setError] = useState("");
  const [searching, setSearching] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (!q.trim()) {
      setItems([]);
      setSearching(false);
      setError("");
      return;
    }
    setSearching(true);
    const handle = window.setTimeout(async () => {
      try {
        const res = await api.search(q.trim());
        setItems(res.items);
        setError("");
      } catch (err) {
        setItems([]);
        setError(err instanceof Error ? err.message : "搜索失败");
      } finally {
        setSearching(false);
      }
    }, 280);
    return () => window.clearTimeout(handle);
  }, [q]);

  async function add(item: SearchItem, event?: FormEvent) {
    event?.preventDefault();
    try {
      await api.addWatchlist(item.code, item.name || "");
      setQ("");
      setItems([]);
      onAdded?.();
      navigate(`/stock/${encodeURIComponent(item.code)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加入自选失败");
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (items[0]) {
      await add(items[0]);
      return;
    }
    const code = q.trim();
    if (!code || searching) return;
    await add({ code, name: "" });
  }

  return (
    <div>
      <form className="search" onSubmit={(e) => void submit(e)}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="搜索美股代码 / 名称，如 AAPL、NVDA、SPY" />
      </form>
      {error && <div className="error">{error}</div>}
      {q.trim() && searching && <div className="muted">搜索中…</div>}
      {q.trim() && !searching && !error && items.length === 0 && (
        <div className="muted">未找到美股。本系统只覆盖美股代码。</div>
      )}
      {items.length > 0 && (
        <ul className="search-pop">
          {items.map((item) => (
            <li key={item.code}>
              <button type="button" onClick={() => add(item)}>
                <strong>{displaySymbol(item.code)}</strong> {item.name || ""}
                <span className="muted"> US</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
