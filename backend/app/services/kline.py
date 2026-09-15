from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

from app.config import get_settings
from app.db import get_cache, set_cache
from app.futu_client import FutuError, get_quote_client
from app.services.serialize import df_records, json_safe, pick

KTYPE_ALIASES = {
    "5m": "K_5M",
    "k_5m": "K_5M",
    "15m": "K_15M",
    "k_15m": "K_15M",
    "60m": "K_60M",
    "1h": "K_60M",
    "k_60m": "K_60M",
    "day": "K_DAY",
    "d": "K_DAY",
    "k_day": "K_DAY",
    "week": "K_WEEK",
    "w": "K_WEEK",
    "k_week": "K_WEEK",
    "month": "K_MON",
    "k_mon": "K_MON",
}

MINUTE_KTYPES = {"K_5M", "K_15M", "K_60M"}
PAGE_SIZE = 1000


def normalize_ktype(raw: str) -> str:
    key = (raw or "K_DAY").strip().lower()
    return KTYPE_ALIASES.get(key, raw.strip().upper())


def _kl_enum(ktype: str) -> Any:
    from futu import KLType

    mapping = {
        "K_5M": KLType.K_5M,
        "K_15M": KLType.K_15M,
        "K_60M": KLType.K_60M,
        "K_DAY": KLType.K_DAY,
        "K_WEEK": KLType.K_WEEK,
        "K_MON": KLType.K_MON,
    }
    if ktype not in mapping:
        raise ValueError(f"不支持的 K 线周期: {ktype}")
    return mapping[ktype]


def default_range(ktype: str) -> tuple[str, str]:
    today = datetime.now(ZoneInfo("America/New_York")).date()
    end = today.isoformat()
    days = {
        "K_5M": 8,
        "K_15M": 16,
        "K_60M": 45,
        "K_DAY": 800,
        "K_WEEK": 365 * 5,
        "K_MON": 365 * 10,
    }.get(ktype, 400)
    start = (today - timedelta(days=days)).isoformat()
    return start, end


def _ttl(ktype: str) -> int:
    settings = get_settings()
    if ktype in MINUTE_KTYPES:
        return settings.kline_cache_ttl_minute_sec
    return settings.kline_cache_ttl_day_sec


def _bar(row: dict[str, Any]) -> dict[str, Any]:
    time_key = pick(row, "time_key", "time")
    return {
        "time": json_safe(time_key),
        "open": pick(row, "open"),
        "high": pick(row, "high"),
        "low": pick(row, "low"),
        "close": pick(row, "close"),
        "volume": pick(row, "volume"),
        "turnover": pick(row, "turnover"),
        "change_rate": pick(row, "change_rate"),
    }


def fetch_history_kline(code: str, ktype: str = "K_DAY", start: str | None = None, end: str | None = None) -> dict[str, Any]:
    ktype = normalize_ktype(ktype)
    if not start or not end:
        start, end = default_range(ktype)
    cache_key = f"{code}|{ktype}|{start}|{end}"
    cached = get_cache("kline_cache", cache_key, _ttl(ktype))
    if cached:
        payload = json.loads(cached)
        payload["cached"] = True
        return payload

    from futu import AuType

    client = get_quote_client()
    kl_type = _kl_enum(ktype)
    page_req_key = None
    rows: list[dict[str, Any]] = []
    for _ in range(20):
        result = client.call(
            "request_history_kline",
            code,
            start=start,
            end=end,
            ktype=kl_type,
            autype=AuType.QFQ,
            max_count=PAGE_SIZE,
            page_req_key=page_req_key,
        )
        if isinstance(result, tuple) and len(result) >= 2:
            data, page_req_key = result[0], result[1]
        else:
            data, page_req_key = result, None
        rows.extend(df_records(data))
        if not page_req_key:
            break
        time.sleep(0.2)

    if not rows:
        raise FutuError(f"未获取到 {code} 的 K 线，请确认对应市场行情权限或 OpenD 状态")

    payload = {
        "code": code,
        "ktype": ktype,
        "start": start,
        "end": end,
        "cached": False,
        "bars": [_bar(row) for row in rows],
        "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    set_cache("kline_cache", cache_key, json.dumps(payload, ensure_ascii=False), {"code": code, "ktype": ktype})
    return payload
