export type UsSession = {
  session: "pre" | "regular" | "after" | "closed" | string;
  label: string;
  et_time?: string | null;
  et_date?: string | null;
  weekday?: string | null;
  holiday?: boolean;
  early_close?: boolean;
};

export type Snapshot = {
  code: string;
  name?: string | null;
  update_time?: string | null;
  last_price?: number | null;
  open_price?: number | null;
  high_price?: number | null;
  low_price?: number | null;
  prev_close_price?: number | null;
  change_val?: number | null;
  change_rate?: number | null;
  volume?: number | null;
  turnover?: number | null;
  turnover_rate?: number | null;
  amplitude?: number | null;
  pe_ratio?: number | null;
  pe_ttm_ratio?: number | null;
  pb_ratio?: number | null;
  total_market_val?: number | null;
  highest52weeks_price?: number | null;
  lowest52weeks_price?: number | null;
  suspension?: boolean | null;
  pre_price?: number | null;
  pre_change_rate?: number | null;
  after_price?: number | null;
  after_change_rate?: number | null;
};

export type WatchlistItem = {
  code: string;
  name: string;
  added_at: string;
};

export type SearchItem = {
  code: string;
  name?: string | null;
  market?: string | null;
  sec_type?: string | null;
};

export type KlineBar = {
  time: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  turnover?: number | null;
};

export type DrawdownPoint = {
  time: string;
  close: number;
  peak: number;
  drawdown: number;
};

export type DrawdownMetrics = {
  code: string;
  current_drawdown: number;
  max_drawdown: number;
  max_drawdown_start?: string | null;
  max_drawdown_end?: string | null;
  underwater_days: number;
  period_return?: number | null;
  rebound_from_trough?: number | null;
  trough_date?: string | null;
  series: DrawdownPoint[];
};

export type NewsItem = {
  title?: string | null;
  source?: string | null;
  publish_time?: string | null;
  url?: string | null;
  news_sub_type?: string | null;
  channel?: string | null;
};

export type NewsSourceStatus = {
  name: string;
  ok: boolean;
  count: number;
  error?: string | null;
};

export type OptionalBlock<T> = {
  available: boolean;
  error?: string | null;
  items: T[];
};

export type HealthResponse = {
  opend: {
    connected: boolean;
    host: string;
    port: number;
    qot_logined?: boolean | null;
    market_us?: string | null;
    market_us_label?: string | null;
    error?: string | null;
  };
  us_session?: UsSession;
  deepseek: {
    configured: boolean;
    model: string;
    base_url: string;
  };
};

export type MarketBoard = {
  top_gainers: OptionalBlock<RankItem>;
  top_losers: OptionalBlock<RankItem>;
  hot_list: OptionalBlock<HotItem>;
};

export type OverviewResponse = {
  opend_connected: boolean;
  error?: string | null;
  market_us?: string | null;
  market_us_label?: string | null;
  us_session?: UsSession;
  watchlist: Snapshot[];
  watchlist_error?: string | null;
  us?: MarketBoard;
  top_gainers: OptionalBlock<RankItem>;
  top_losers: OptionalBlock<RankItem>;
  hot_list: OptionalBlock<HotItem>;
};

export type RankItem = {
  code?: string | null;
  name?: string | null;
  last_price?: number | null;
  change_rate?: number | null;
  turnover?: number | null;
};

export type HotItem = {
  code?: string | null;
  name?: string | null;
  average_heat?: number | null;
  news_title?: string | null;
  news_url?: string | null;
};

export type ReportResponse = {
  code: string;
  markdown: string;
  created_at: string;
  cached?: boolean;
  expired?: boolean;
  logic?: AnalysisResponse;
};

export type LogicDimension = {
  id: string;
  title: string;
  score: number;
  stance: string;
  summary: string;
  evidence: string[];
};

export type AnalysisLogic = AnalysisResponse;

export type AnalysisResponse = {
  version: string;
  framework: string;
  framework_note: string;
  code: string;
  market?: string;
  symbol?: string;
  name?: string;
  verdict: {
    bias: string;
    score: number;
    confidence: string;
    one_liner: string;
  };
  dimensions: LogicDimension[];
  levels: {
    last_close?: number | null;
    supports: { name: string; price: number }[];
    resistances: { name: string; price: number }[];
    invalidation?: string;
  };
  watchlist: string[];
  disclaimer?: string;
};

export type SettingsResponse = {
  futu_host: string;
  futu_port: number;
  deepseek_configured: boolean;
  deepseek_model: string;
  deepseek_base_url: string;
  report_cache_hours: number;
};
