import { useEffect, useState } from "react";
import { api } from "../api";
import type { HealthResponse, SettingsResponse } from "../types";

export default function Settings() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.settings(), api.health()])
      .then(([s, h]) => {
        setSettings(s);
        setHealth(h);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "设置加载失败"));
  }, []);

  return (
    <div className="stack">
      <div className="card">
        <h2>连接与密钥</h2>
        <p className="muted">配置写在项目根目录 `.env`，不在此页明文展示 DeepSeek Key。</p>
        {error && <div className="error">{error}</div>}
        <table>
          <tbody>
            <tr>
              <td>OpenD Host</td>
              <td>{settings?.futu_host}</td>
            </tr>
            <tr>
              <td>OpenD Port</td>
              <td>{settings?.futu_port}</td>
            </tr>
            <tr>
              <td>OpenD 状态</td>
              <td className={health?.opend.connected ? "up" : "down"}>
                {health?.opend.connected ? "已连接" : health?.opend.error || "未连接"}
              </td>
            </tr>
            <tr>
              <td>行情登录</td>
              <td>{health?.opend.qot_logined ? "是" : "否 / 未知"}</td>
            </tr>
            <tr>
              <td>美股时段</td>
              <td>
                {health?.us_session
                  ? `${health.us_session.label} · ${health.us_session.weekday || ""} ${health.us_session.et_time || ""}`.trim()
                  : health?.opend.market_us_label || health?.opend.market_us || "—"}
              </td>
            </tr>
            <tr>
              <td>DeepSeek</td>
              <td>{settings?.deepseek_configured ? "已配置" : "未配置"}</td>
            </tr>
            <tr>
              <td>模型</td>
              <td>{settings?.deepseek_model}</td>
            </tr>
            <tr>
              <td>Base URL</td>
              <td>{settings?.deepseek_base_url}</td>
            </tr>
            <tr>
              <td>报告缓存</td>
              <td>{settings?.report_cache_hours} 小时 / 标的</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
