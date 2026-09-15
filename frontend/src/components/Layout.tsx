import { useCallback, useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import type { HealthResponse, Snapshot, WatchlistItem } from "../types";
import HealthBanner from "./HealthBanner";
import WatchlistSidebar from "./WatchlistSidebar";
import { sessionLine } from "../utils";

export default function Layout() {
  const location = useLocation();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Snapshot>>({});
  const [menuOpen, setMenuOpen] = useState(false);

  const refresh = useCallback(async () => {
    let connected = false;
    try {
      const next = await api.health();
      setHealth(next);
      connected = Boolean(next.opend.connected);
    } catch {
      setHealth({
        opend: { connected: false, host: "127.0.0.1", port: 11111, error: "后端健康检查失败" },
        deepseek: { configured: false, model: "", base_url: "" },
      });
    }
    try {
      const wl = await api.watchlist();
      setWatchlist(wl.items);
    } catch {
      setWatchlist([]);
    }
    if (!connected) {
      setQuotes({});
      return;
    }
    try {
      const ov = await api.overview();
      const map: Record<string, Snapshot> = {};
      for (const snap of ov.watchlist || []) {
        if (snap.code) map[snap.code] = snap;
      }
      setQuotes(map);
    } catch {
      setQuotes({});
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = window.setInterval(() => void refresh(), 15000);
    return () => window.clearInterval(id);
  }, [refresh]);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = previous;
      window.removeEventListener("keydown", onKey);
    };
  }, [menuOpen]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <button
          type="button"
          className="menu-btn"
          aria-expanded={menuOpen}
          aria-controls="watchlist-sidebar"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? "关闭" : "自选"}
        </button>
        <div className="brand">
          <div className="brand-name">
            <h1>美股投研</h1>
          </div>
          <span className="session">
            {health?.opend.connected
              ? `OpenD 已连接 · ${sessionLine(health.us_session)}`
              : "OpenD 未连接"}
          </span>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            总览
          </NavLink>
          <NavLink to="/watchlist">自选</NavLink>
          <NavLink to="/settings">设置</NavLink>
        </nav>
      </header>
      <HealthBanner health={health} />
      {menuOpen ? (
        <button type="button" className="sidebar-mask" aria-label="关闭自选" onClick={() => setMenuOpen(false)} />
      ) : null}
      <WatchlistSidebar open={menuOpen} items={watchlist} quotes={quotes} onRefresh={refresh} />
      <main className="main">
        <Outlet context={{ health, watchlist, quotes, refresh }} />
      </main>
    </div>
  );
}
