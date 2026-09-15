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
        cur.execute("DELETE FROM watchlist WHERE code NOT LIKE 'US.%'")
        cur.execute("DELETE FROM reports WHERE code NOT LIKE 'US.%'")
        now = utc_now()
        for code, name in DEFAULT_WATCHLIST:
            cur.execute("SELECT 1 FROM watchlist WHERE code = ?", (code,))
            if cur.fetchone() is None:
                cur.execute(
                    "INSERT INTO watchlist (code, name, added_at) VALUES (?, ?, ?)",
                    (code, name, now),
                )


def list_watchlist() -> list[dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT code, name, added_at FROM watchlist WHERE code LIKE 'US.%' ORDER BY added_at ASC")
        return [dict(row) for row in cur.fetchall()]


def add_watchlist(code: str, name: str = "") -> dict[str, Any]:
    now = utc_now()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO watchlist (code, name, added_at)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET name = excluded.name
            """,
            (code, name, now),
        )
        cur.execute("SELECT code, name, added_at FROM watchlist WHERE code = ?", (code,))
        return dict(cur.fetchone())


def remove_watchlist(code: str) -> bool:
    with db_cursor() as cur:
        cur.execute("DELETE FROM watchlist WHERE code = ?", (code,))
        return cur.rowcount > 0


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
        cur.execute("SELECT markdown, created_at FROM reports WHERE code = ?", (code,))
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
            "expired": expired,
            "age_sec": int(age),
        }


def save_report(code: str, markdown: str) -> dict[str, Any]:
    now = utc_now()
    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO reports (code, markdown, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                markdown = excluded.markdown,
                created_at = excluded.created_at
            """,
            (code, markdown, now),
        )
    return {"code": code, "markdown": markdown, "created_at": now, "expired": False, "cached": False}
