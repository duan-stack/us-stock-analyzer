import type {
  AnalysisLogic,
  DrawdownMetrics,
  HealthResponse,
  NewsItem,
  NewsSourceStatus,
  OptionalBlock,
  OverviewResponse,
  ReportResponse,
  SearchItem,
  SettingsResponse,
  Snapshot,
  WatchlistItem,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function formatDetail(body: unknown, fallback: string): string {
  if (typeof body === "string" && body.trim()) return body.trim();
  if (!body || typeof body !== "object") return fallback;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return detail.trim();
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (typeof item === "string") return item;
      if (item && typeof item === "object" && "msg" in item) return String((item as { msg: unknown }).msg);
      return "";
    });
    const text = parts.filter(Boolean).join("；");
    if (text) return text;
  }
  return fallback;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers });
  const raw = await res.text();
  let body: unknown = {};
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      body = raw;
    }
  }
  if (!res.ok) {
    throw new ApiError(res.status, formatDetail(body, res.statusText || `请求失败 (${res.status})`));
  }
  return body as T;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),
  settings: () => request<SettingsResponse>("/api/settings"),
  overview: () => request<OverviewResponse>("/api/market/overview"),
  watchlist: () => request<{ items: WatchlistItem[] }>("/api/watchlist"),
  addWatchlist: (code: string, name = "") =>
    request<{ item: WatchlistItem }>("/api/watchlist", {
      method: "POST",
      body: JSON.stringify({ code, name }),
    }),
  removeWatchlist: (code: string) =>
    request<{ ok: boolean }>(`/api/watchlist/${encodeURIComponent(code)}`, { method: "DELETE" }),
  search: (q: string) => request<{ items: SearchItem[] }>(`/api/stocks/search?q=${encodeURIComponent(q)}`),
  snapshot: (code: string) => request<Snapshot>(`/api/stocks/${encodeURIComponent(code)}/snapshot`),
  kline: (code: string, ktype: string) =>
    request<{ code: string; ktype: string; cached: boolean; bars: import("./types").KlineBar[] }>(
      `/api/stocks/${encodeURIComponent(code)}/kline?ktype=${encodeURIComponent(ktype)}`,
    ),
  drawdown: (code: string) => request<DrawdownMetrics>(`/api/stocks/${encodeURIComponent(code)}/drawdown`),
  news: (code: string) =>
    request<{ items: NewsItem[]; cached?: boolean; sources?: NewsSourceStatus[] }>(
      `/api/stocks/${encodeURIComponent(code)}/news`,
    ),
  plates: (code: string) =>
    request<OptionalBlock<{ plate_name?: string; plate_type?: string; plate_code?: string }>>(
      `/api/stocks/${encodeURIComponent(code)}/plates`,
    ),
  capitalFlow: (code: string) =>
    request<OptionalBlock<{ time?: string; in_flow?: number }>>(`/api/stocks/${encodeURIComponent(code)}/capital-flow`),
  profile: (code: string) =>
    request<OptionalBlock<{ name?: string; value?: string }>>(`/api/stocks/${encodeURIComponent(code)}/profile`),
  analysis: (code: string) => request<AnalysisLogic>(`/api/stocks/${encodeURIComponent(code)}/analysis`),
  getReport: (code: string) => request<ReportResponse>(`/api/stocks/${encodeURIComponent(code)}/ai-report`),
  generateReport: (code: string, force = false) =>
    request<ReportResponse>(`/api/stocks/${encodeURIComponent(code)}/ai-report`, {
      method: "POST",
      body: JSON.stringify({ force }),
    }),
};
