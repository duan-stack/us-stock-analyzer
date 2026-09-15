import type { NewsItem, NewsSourceStatus } from "../types";

export default function NewsList({
  items,
  error,
  sources,
}: {
  items: NewsItem[];
  error?: string;
  sources?: NewsSourceStatus[];
}) {
  if (error) return <div className="error">{error}</div>;
  return (
    <div>
      {sources && sources.length > 0 && (
        <div className="chips" style={{ marginBottom: 10 }}>
          {sources.map((source) => (
            <span key={source.name} className={`chip ${source.ok ? "" : "chip-off"}`} title={source.error || ""}>
              {source.name}
              {source.ok ? ` ${source.count}` : " 未取到"}
            </span>
          ))}
        </div>
      )}
      {!items.length ? (
        <div className="muted">暂无资讯。若各来源均未取到，请稍后重试。</div>
      ) : (
        items.map((item, idx) => (
          <div className="news-item" key={`${item.url || item.title}-${idx}`}>
            <div className="meta">
              {item.publish_time || ""}
              {item.publish_time ? " · " : ""}
              <span className="chip">{item.source || item.news_sub_type || "资讯"}</span>
            </div>
            {item.url ? (
              <a href={item.url} target="_blank" rel="noreferrer">
                {item.title || item.url}
              </a>
            ) : (
              <div>{item.title}</div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
