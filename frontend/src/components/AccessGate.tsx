import { FormEvent, ReactNode, useEffect, useState } from "react";
import { api, ApiError } from "../api";

export default function AccessGate({ children }: { children: ReactNode }) {
  const [checking, setChecking] = useState(true);
  const [required, setRequired] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [token, setToken] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await api.accessStatus();
        if (cancelled) return;
        if (!status.required) {
          setRequired(false);
          setUnlocked(true);
          return;
        }
        setRequired(true);
        // Probe an authenticated endpoint via cookie; health is public.
        try {
          await api.watchlist();
          if (!cancelled) setUnlocked(true);
        } catch (err) {
          if (!cancelled) {
            setUnlocked(!(err instanceof ApiError && err.status === 401));
          }
        }
      } catch {
        if (!cancelled) {
          setRequired(false);
          setUnlocked(true);
        }
      } finally {
        if (!cancelled) setChecking(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await api.accessLogin(token.trim());
      setUnlocked(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "口令不正确");
    }
  }

  if (checking) {
    return <div className="muted" style={{ padding: 24 }}>检查访问权限…</div>;
  }
  if (!required || unlocked) {
    return <>{children}</>;
  }

  return (
    <div className="access-gate">
      <form className="card access-card" onSubmit={(e) => void submit(e)}>
        <h2>访问口令</h2>
        <p className="muted">站点已开启访问保护。输入口令后继续使用美股投研。</p>
        <input
          type="password"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="ACCESS_TOKEN"
          autoFocus
        />
        {error ? <div className="error">{error}</div> : null}
        <button className="btn primary" type="submit" disabled={!token.trim()}>
          进入
        </button>
      </form>
    </div>
  );
}
