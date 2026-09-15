export function displaySymbol(code: string): string {
  const i = code.indexOf(".");
  if (i < 0) return code;
  const market = code.slice(0, i);
  const symbol = code.slice(i + 1);
  if (market === "US") return symbol;
  return symbol || code;
}

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function formatCompact(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
  return formatNumber(value, 2);
}

export function formatPct(value: number | null | undefined, alreadyPercent = false): string {
  if (value == null || Number.isNaN(value)) return "—";
  const pct = alreadyPercent ? value : value * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(2)}%`;
}

export function signedClass(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value) || value === 0) return "flat";
  return value > 0 ? "up" : "down";
}

export function dateOnly(value?: string | null): string {
  if (!value) return "—";
  return value.replace("T", " ").slice(0, 10);
}

export function sessionLine(session?: { label?: string | null; et_time?: string | null; weekday?: string | null } | null): string {
  if (!session) return "美股时段未知";
  const parts = [session.label, session.weekday, session.et_time].filter(Boolean);
  return parts.join(" · ");
}
