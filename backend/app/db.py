from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import get_settings

DEFAULT_WATCHLIST = [
    ("US.AAPL", "苹果"),
    ("US.NVDA", "英伟达"),
    ("US.MSFT", "微软"),
    ("US.AMZN", "亚马逊"),
    ("US.GOOGL", "谷歌"),
    ("US.META", "Meta"),
    ("US.TSLA", "特斯拉"),
    ("US.SPY", "标普500 ETF"),
    ("US.QQQ", "纳斯达克100 ETF"),
]

_local = threading.local()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _connect() -> sqlite3.Connection:
    settings = get_settings()
    path = Path(settings.sqlite_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def get_conn() -> sqlite3.Connection:
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = _connect()
        _local.conn = conn
    return conn


@contextmanager
def db_cursor() -> Iterator[sqlite3.Cursor]:
    conn = get_conn()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def _table_columns(cur: sqlite3.Cursor, table: str) -> set[str]:
    cur.execute(f"PRAGMA table_info({table})")
    return {str(row["name"]) for row in cur.fetchall()}


def init_db() -> None:
    with db_cursor() as cur:
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                added_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS kline_cache (
                cache_key TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                ktype TEXT NOT NULL,
                payload TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS news_cache (
                cache_key TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                code TEXT PRIMARY KEY,
                markdown TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        wl_cols = _table_columns(cur, "watchlist")
        if "pinned" not in wl_cols:
            cur.execute("ALTER TABLE watchlist ADD COLUMN pinned INTEGER NOT NULL DEFAULT 0")
        if "sort_order" not in wl_cols:
            cur.execute("ALTER TABLE watchlist ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
        report_cols = _table_columns(cur, "reports")
        if "logic_json" not in report_cols:
            cur.execute("ALTER TABLE reports ADD COLUMN logic_json TEXT NOT NULL DEFAULT ''")

        cur.execute("DELETE FROM watchlist WHERE code NOT LIKE 'US.%'")
        cur.execute("DELETE FROM reports WHERE code NOT LIKE 'US.%'")
        now = utc_now()
        for idx, (code, name) in enumerate(DEFAULT_WATCHLIST):
            cur.execute("SELECT 1 FROM watchlist WHERE code = ?", (code,))
            if cur.fetchone() is None:
                cur.execute(
                    "INSERT INTO watchlist (code, name, added_at, pinned, sort_order) VALUES (?, ?, ?, 0, ?)",
                    (code, name, now, idx),
                )


def list_watchlist() -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT code, name, added_at, pinned, sort_order
            FROM watchlist
            WHERE code LIKE 'US.%'
            ORDER BY pinned DESC, sort_order ASC, added_at ASC
            """
        )
        rows = []
        for row in cur.fetchall():
            item = dict(row)
            item["pinned"] = bool(item.get("pinned"))
            rows.append(item)
        return rows


def add_watchlist(code: str, name: str = "") -> dict[str, Any]:
    now = utc_now()
    with db_cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 AS next_order FROM watchlist")
        next_order = int(cur.fetchone()["next_order"] or 0)
        cur.execute(
            """
            INSERT INTO watchlist (code, name, added_at, pinned, sort_order)
            VALUES (?, ?, ?, 0, ?)
            ON CONFLICT(code) DO UPDATE SET name = excluded.name
            """,
            (code, name, now, next_order),
        )
        cur.execute(
            "SELECT code, name, added_at, pinned, sort_order FROM watchlist WHERE code = ?",
            (code,),
        )
        item = dict(cur.fetchone())
        item["pinned"] = bool(item.get("pinned"))
        return item


def set_watchlist_pinned(code: str, pinned: bool) -> dict[str, Any] | None:
    with db_cursor() as cur:
        cur.execute("UPDATE watchlist SET pinned = ? WHERE code = ?", (1 if pinned else 0, code))
        if cur.rowcount <= 0:
            return None
        cur.execute(
            "SELECT code, name, added_at, pinned, sort_order FROM watchlist WHERE code = ?",
            (code,),
        )
        row = cur.fetchone()
        if not row:
            return None
        item = dict(row)
        item["pinned"] = bool(item.get("pinned"))
        return item


def reorder_watchlist(codes: list[str]) -> list[dict[str, Any]]:
    with db_cursor() as cur:
        for idx, code in enumerate(codes):
            cur.execute("UPDATE watchlist SET sort_order = ? WHERE code = ?", (idx, code))
    return list_watchlist()


def remove_watchlist(code: str) -> bool:
    with db_cursor() as cur:
        cur.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        return cur.rowcount > 0


def cache_stats() -> dict[str, int]:
    with db_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM kline_cache")
        kline = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM news_cache")
        news = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM reports")
        reports = int(cur.fetchone()["c"])
        cur.execute("SELECT COUNT(*) AS c FROM watchlist WHERE code LIKE 'US.%'")
        watch = int(cur.fetchone()["c"])
    return {"kline_cache": kline, "news_cache": news, "reports": reports, "watchlist": watch}


def get_cache(table: str, cache_key: str, ttl_sec: int) -> str | None:
    with db_cursor() as cur:
        cur.execute(
            f"SELECT payload, fetched_at FROM {table} WHERE cache_key = ?",
            (cache_key,),
        )
        row = cur.fetchone()
        if not row:
            return None
        fetched = datetime.fromisoformat(row["fetched_at"])
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - fetched).total_seconds()
        if age > ttl_sec:
            return None
        return str(row["payload"])


def set_cache(table: str, cache_key: str, payload: str, extra: dict[str, Any] | None = None) -> None:
    extra = extra or {}
    with db_cursor() as cur:
        if table == "kline_cache":
            cur.execute(
                """
                INSERT INTO kline_cache (cache_key, code, ktype, payload, fetched_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    fetched_at = excluded.fetched_at
                """,
                (cache_key, extra.get("code", ""), extra.get("ktype", ""), payload, utc_now()),
            )
        else:
            cur.execute(
                f"""
                INSERT INTO {table} (cache_key, payload, fetched_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload = excluded.payload,
                    fetched_at = excluded.fetched_at
                """,
                (cache_key, payload, utc_now()),
            )


def get_report(code: str, ttl_sec: int) -> dict[str, Any] | None:
    with db_cursor() as cur:
        cur.execute("SELECT markdown, created_at, logic_json FROM reports WHERE code = ?", (code,))
        row = cur.fetchone()
        if not row:
            return None
        created = datetime.fromisoformat(row["created_at"])
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - created).total_seconds()
        expired = age > ttl_sec
        return {
            "code": code,
            "markdown": row["markdown"],
            "created_at": row["created_at"],
            "logic_json": row["logic_json"] or "",
            "expired": expired,
            "age_sec": int(age),
        }


def save_report(code: str, markdown: str, logic_json: str = "") -> dict[str, Any]:
    now = utc_now()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO reports (code, markdown, created_at, logic_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                markdown = excluded.markdown,
                created_at = excluded.created_at,
                logic_json = excluded.logic_json
            """,
            (code, markdown, now, logic_json),
        )
    return {
        "code": code,
        "markdown": markdown,
        "created_at": now,
        "logic_json": logic_json,
        "expired": False,
        "cached": False,
    }
