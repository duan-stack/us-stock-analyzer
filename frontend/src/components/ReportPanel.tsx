import { useEffect, useState } from "react";
import Markdown from "react-markdown";
import { api } from "../api";
import type { AnalysisLogic, ReportResponse } from "../types";
import LogicBoard from "./LogicBoard";

export default function ReportPanel({ code }: { code: string }) {
  const [logic, setLogic] = useState<AnalysisLogic | null>(null);
  const [logicError, setLogicError] = useState("");
  const [report, setReport] = useState<ReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setReport(null);
    setLogic(null);
    setError("");
    setLogicError("");
    const loadLogic = () =>
      api.analysis(code).catch(async () => {
        await new Promise((resolve) => window.setTimeout(resolve, 600));
        return api.analysis(code);
      });
    loadLogic()
      .then(setLogic)
      .catch((err) => setLogicError(err instanceof Error ? err.message : "分析框架加载失败"));
    api
      .getReport(code)
      .then(setReport)
      .catch(() => setReport(null));
  }, [code]);

  async function generate(force: boolean) {
    setLoading(true);
    setError("");
    try {
      const next = await api.generateReport(code, force);
      setReport(next);
      if (next.logic) setLogic(next.logic);
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成报告失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="card">
      <div className="row-between">
        <h3 style={{ margin: 0 }}>四维分析</h3>
        <div className="report-actions">
          <button className="btn primary" disabled={loading} onClick={() => generate(false)}>
            {loading ? "生成中…" : "生成 AI 解读"}
          </button>
          <button className="btn" disabled={loading || !report} onClick={() => generate(true)}>
            强制刷新
          </button>
        </div>
      </div>
      <p className="muted">
        先按固定规则给这支股票打分（趋势、位置动量、回撤风险、估值事件），再让 AI 解释这套结论，而不是自由发挥。
      </p>
      {logicError && <div className="error">{logicError}</div>}
      {logic && <LogicBoard logic={logic} />}
      {report?.created_at && (
        <div className="muted" style={{ margin: "8px 0" }}>
          {report.cached ? "缓存解读 · " : "新生成 · "}
          {report.created_at} · 同标的 6 小时内复用
        </div>
      )}
      {error && <div className="error">{error}</div>}
      {report?.markdown ? (
        <div className="markdown">
          <Markdown>{report.markdown}</Markdown>
        </div>
      ) : (
        !loading && <div className="muted">规则结论已在上方。需要叙述性解读时，再生成 AI 报告。</div>
      )}
    </div>
  );
}
