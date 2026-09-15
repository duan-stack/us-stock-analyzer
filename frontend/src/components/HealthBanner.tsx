import type { HealthResponse } from "../types";

export default function HealthBanner({ health }: { health: HealthResponse | null }) {
  if (!health) return <div className="banner">正在检查 FutuOpenD 连接…</div>;
  if (health.opend.connected) return null;
  return (
    <div className="banner">
      请启动 FutuOpenD（{health.opend.host}:{health.opend.port}）。
      {health.opend.error ? ` ${health.opend.error}` : ""}
      未连通时不会展示虚构行情。
    </div>
  );
}
