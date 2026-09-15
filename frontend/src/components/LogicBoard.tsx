import type { AnalysisLogic } from "../types";

function biasClass(bias?: string) {
  if (bias === "偏多") return "up";
  if (bias === "偏空") return "down";
  return "flat";
}

export default function LogicBoard({ logic }: { logic: AnalysisLogic }) {
  const verdict = logic.verdict;
  return (
    <div className="logic-board">
      <div className="logic-verdict">
        <div>
          <div className="muted">{logic.framework} · 把握 {verdict.confidence}</div>
          <div className={`logic-bias ${biasClass(verdict.bias)}`}>
            {verdict.bias}
            <span className="muted" style={{ marginLeft: 8, fontSize: 13, fontWeight: 500 }}>
              {verdict.score > 0 ? "+" : ""}
              {verdict.score} 分
            </span>
          </div>
        </div>
        <p className="muted" style={{ margin: 0, maxWidth: 520 }}>
          {verdict.one_liner}
        </p>
      </div>
      <p className="muted logic-note">{logic.framework_note}</p>
      <div className="logic-grid">
        {logic.dimensions.map((dim) => (
          <div className="logic-dim" key={dim.id}>
            <div className="row-between">
              <strong>{dim.title}</strong>
              <span className={biasClass(dim.stance)}>
                {dim.stance} {dim.score > 0 ? "+" : ""}
                {dim.score}
              </span>
            </div>
            <p>{dim.summary}</p>
            <ul>
              {(dim.evidence || []).slice(0, 4).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="logic-levels">
        <div>
          <div className="muted">支撑</div>
          <div>
            {(logic.levels.supports || []).slice(0, 3).map((item) => (
              <span className="chip" key={`s-${item.name}`}>
                {item.name} {item.price}
              </span>
            ))}
            {!logic.levels.supports?.length && <span className="muted">—</span>}
          </div>
        </div>
        <div>
          <div className="muted">压力</div>
          <div>
            {(logic.levels.resistances || []).slice(0, 3).map((item) => (
              <span className="chip" key={`r-${item.name}`}>
                {item.name} {item.price}
              </span>
            ))}
            {!logic.levels.resistances?.length && <span className="muted">—</span>}
          </div>
        </div>
      </div>
      <p className="muted">{logic.levels.invalidation}</p>
      {logic.disclaimer ? <p className="muted">{logic.disclaimer}</p> : null}
    </div>
  );
}
