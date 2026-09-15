from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Callable
from urllib.parse import quote, quote_plus

import httpx

from app.codes import display_symbol, yahoo_symbol
from app.config import get_settings
from app.db import get_cache, set_cache
from app.futu_client import FutuError, get_quote_client
from app.services.serialize import df_records, pick

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/rss+xml, application/xml, application/json, text/html, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def _news_item(row: dict[str, Any]) -> dict[str, Any]:
    related = row.get("related_securities") or []
    if isinstance(related, str):
        related = [related]
    return {
        "title": pick(row, "title"),
        "source": pick(row, "source") or "富途",
        "publish_time": pick(row, "publish_time"),
        "url": pick(row, "url"),
        "news_sub_type": pick(row, "news_sub_type") or "富途",
        "view_count": pick(row, "view_count"),
        "related_securities": related,
        "channel": "futu",
    }


def _local_tag(node: ET.Element) -> str:
    return (node.tag or "").split("}")[-1].lower()


def _child_text(node: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in list(node):
        if _local_tag(child) in wanted:
            text = "".join(child.itertext()).strip()
            if text:
                return text
            href = child.attrib.get("href") or child.attrib.get("url")
            if href:
                return href.strip()
    return ""


def _iso_time(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc).replace(microsecond=0).isoformat()
    text = str(value).strip()
    if text.isdigit():
        return _iso_time(int(text))
    try:
        parsed = parsedate_to_datetime(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()
    except ValueError:
        return text


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\u4e00-\u9fff]+", " ", (title or "").lower())).strip()


def merge_news_items(batches: list[list[dict[str, Any]]], limit: int = 20) -> list[dict[str, Any]]:
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    merged: list[dict[str, Any]] = []
    for batch in batches:
        for item in batch:
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not title and not url:
                continue
            title_key = _norm_title(title)
            if url and url in seen_urls:
                continue
            if title_key and title_key in seen_titles:
                continue
            if url:
                seen_urls.add(url)
            if title_key:
                seen_titles.add(title_key)
            merged.append(item)

    def _sort_key(item: dict[str, Any]) -> str:
        return str(item.get("publish_time") or "")

    merged.sort(key=_sort_key, reverse=True)
    return merged[:limit]


def _item(
    *,
    title: str,
    url: str,
    source: str,
    publish_time: Any,
    channel: str,
    news_sub_type: str | None = None,
) -> dict[str, Any]:
    return {
        "title": title.strip(),
        "url": url.strip(),
        "source": source.strip() or channel,
        "publish_time": _iso_time(publish_time),
        "news_sub_type": news_sub_type or channel,
        "view_count": None,
        "related_securities": [],
        "channel": channel,
    }


def _http_get(url: str, timeout: float = 8.0) -> httpx.Response:
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=_HTTP_HEADERS) as client:
        response = client.get(url)
        response.raise_for_status()
        return response


def _parse_rss(xml_text: str, *, default_source: str, channel: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items
    for node in root.iter():
        if _local_tag(node) not in {"item", "entry"}:
            continue
        title = _child_text(node, "title")
        link = _child_text(node, "link", "id")
        if not link:
            for child in list(node):
                if _local_tag(child) == "link":
                    link = (child.attrib.get("href") or "").strip()
                    if link:
                        break
        published = _child_text(node, "pubdate", "published", "updated", "date")
        source = _child_text(node, "source", "publisher", "author") or default_source
        if title or link:
            items.append(
                _item(
                    title=title or link,
                    url=link,
                    source=source,
                    publish_time=published,
                    channel=channel,
                    news_sub_type=default_source,
                )
            )
    return items


def _keywords(code: str, name: str) -> list[str]:
    parts = [
        display_symbol(code),
        yahoo_symbol(code),
        code,
        name.strip() if name else "",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for part in parts:
        value = str(part or "").strip()
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _google_query(code: str, name: str) -> str:
    keys = _keywords(code, name)
    quoted = [f'"{key}"' if " " in key else key for key in keys[:4]]
    extra = "stock OR earnings OR shares"
    return " ".join(quoted + [extra])


def _fetch_futu(code: str, name: str, max_count: int) -> tuple[list[dict[str, Any]], str | None]:
    keyword = " ".join(_keywords(code, name)[:3])
    client = get_quote_client()
    try:
        from futu import NewsSubType

        data = client.call("get_search_news", keyword, max_count, news_sub_type=NewsSubType.ALL)
    except Exception:
        data = client.call("get_search_news", keyword, max_count)
    return [_news_item(row) for row in df_records(data)], None


def _fetch_yahoo(code: str, name: str, max_count: int) -> tuple[list[dict[str, Any]], str | None]:
    symbol = yahoo_symbol(code)
    lang = "en-US"
    region = "US"
    search_url = (
        "https://query1.finance.yahoo.com/v1/finance/search"
        f"?q={quote(symbol)}&quotesCount=0&newsCount={max_count}&lang={lang}&region={region}"
    )
    try:
        payload = _http_get(search_url).json()
        raw_items = payload.get("news") if isinstance(payload, dict) else None
        items: list[dict[str, Any]] = []
        if isinstance(raw_items, list):
            for row in raw_items:
                if not isinstance(row, dict):
                    continue
                title = str(row.get("title") or "").strip()
                link = str(row.get("link") or row.get("url") or "").strip()
                if not title:
                    continue
                items.append(
                    _item(
                        title=title,
                        url=link,
                        source=str(row.get("publisher") or "Yahoo Finance"),
                        publish_time=row.get("providerPublishTime"),
                        channel="yahoo",
                        news_sub_type="Yahoo Finance",
                    )
                )
        if items:
            return items, None
    except Exception:
        pass
    rss_url = (
        "https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={quote(symbol)}&region={region}&lang={lang}"
    )
    xml_text = _http_get(rss_url).text
    items = _parse_rss(xml_text, default_source="Yahoo Finance", channel="yahoo")
    if not items:
        return [], "Yahoo Finance 未返回条目"
    return items, None


def _fetch_google(code: str, name: str, max_count: int) -> tuple[list[dict[str, Any]], str | None]:
    query = _google_query(code, name)
    collected: list[list[dict[str, Any]]] = []
    last_error: str | None = None
    for hl, gl, ceid in (("zh-CN", "CN", "CN:zh-CN"), ("en-US", "US", "US:en")):
        url = (
            "https://news.google.com/rss/search"
            f"?q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={quote(ceid)}"
        )
        try:
            xml_text = _http_get(url).text
            items = _parse_rss(xml_text, default_source="Google 新闻", channel="google")
            collected.append(items[:max_count])
        except Exception as exc:
            last_error = str(exc)
    merged = merge_news_items(collected, limit=max_count)
    if not merged:
        return [], last_error or "Google 新闻未返回条目"
    return merged, None


def _fetch_sina(code: str, name: str, max_count: int) -> tuple[list[dict[str, Any]], str | None]:
    keyword = (name or display_symbol(code)).strip()
    url = (
        "https://feed.mix.sina.com.cn/api/roll/get"
        f"?pageid=153&lid=2516&num={max_count}&version=1.0&k={quote(keyword)}"
    )
    payload = _http_get(url).json()
    rows = (((payload or {}).get("result") or {}).get("data")) if isinstance(payload, dict) else None
    items: list[dict[str, Any]] = []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            link = str(row.get("url") or row.get("wapurl") or "").strip()
            if not title:
                continue
            items.append(
                _item(
                    title=title,
                    url=link,
                    source=str(row.get("media_name") or row.get("source") or "新浪财经"),
                    publish_time=row.get("ctime") or row.get("intime"),
                    channel="sina",
                    news_sub_type="新浪财经",
                )
            )
    if not items:
        return [], "新浪财经未返回条目"
    return items, None


def search_news(code: str, name: str = "", max_count: int = 20) -> dict[str, Any]:
    settings = get_settings()
    cache_key = f"news3|{code}|{max_count}|{name}"
    cached = get_cache("news_cache", cache_key, settings.news_cache_ttl_sec)
    if cached:
        payload = json.loads(cached)
        payload["cached"] = True
        return payload

    fetchers: list[tuple[str, Callable[[], tuple[list[dict[str, Any]], str | None]]]] = [
        ("Yahoo Finance", lambda: _fetch_yahoo(code, name, max_count)),
        ("Google 新闻", lambda: _fetch_google(code, name, max_count)),
        ("新浪财经", lambda: _fetch_sina(code, name, max_count)),
        ("富途", lambda: _fetch_futu(code, name, max_count)),
    ]
    batches: list[list[dict[str, Any]]] = []
    sources: list[dict[str, Any]] = []

    def _run(label: str, fn: Callable[[], tuple[list[dict[str, Any]], str | None]]) -> dict[str, Any]:
        try:
            items, error = fn()
            return {"name": label, "ok": not error, "count": len(items), "error": error, "items": items}
        except Exception as exc:
            return {"name": label, "ok": False, "count": 0, "error": str(exc), "items": []}

    pool = ThreadPoolExecutor(max_workers=4)
    try:
        futures = {pool.submit(_run, label, fn): label for label, fn in fetchers}
        pending = set(futures)
        try:
            for future in as_completed(futures, timeout=18):
                pending.discard(future)
                result = future.result()
                batches.append(result.get("items") or [])
                sources.append(
                    {
                        "name": result["name"],
                        "ok": result["ok"] and result["count"] > 0,
                        "count": result["count"],
                        "error": None if result["count"] else result.get("error"),
                    }
                )
        except FuturesTimeout:
            for future in pending:
                sources.append(
                    {
                        "name": futures[future],
                        "ok": False,
                        "count": 0,
                        "error": "超时",
                    }
                )
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    source_order = {label: idx for idx, (label, _) in enumerate(fetchers)}
    sources.sort(key=lambda row: source_order.get(str(row.get("name")), 99))
    items = merge_news_items(batches, limit=max_count)
    payload = {
        "code": code,
        "keyword": " ".join(_keywords(code, name)),
        "cached": False,
        "items": items,
        "sources": sources,
    }
    set_cache("news_cache", cache_key, json.dumps(payload, ensure_ascii=False))
    return payload


def optional_owner_plate(code: str) -> dict[str, Any]:
    try:
        data = get_quote_client().call("get_owner_plate", [code])
        items = []
        for row in df_records(data):
            items.append(
                {
                    "code": pick(row, "code"),
                    "name": pick(row, "name"),
                    "plate_code": pick(row, "plate_code"),
                    "plate_name": pick(row, "plate_name"),
                    "plate_type": pick(row, "plate_type"),
                }
            )
        return {"available": True, "items": items}
    except FutuError as exc:
        return {"available": False, "error": exc.message, "items": []}
    except Exception as exc:
        return {"available": False, "error": str(exc), "items": []}


def optional_capital_flow(code: str) -> dict[str, Any]:
    from datetime import date, timedelta

    client = get_quote_client()
    end = date.today()
    start = end - timedelta(days=40)
    try:
        from futu import PeriodType

        try:
            data = client.call(
                "get_capital_flow",
                code,
                period_type=PeriodType.DAY,
                start=start.isoformat(),
                end=end.isoformat(),
            )
        except Exception:
            data = client.call("get_capital_flow", code, period_type=PeriodType.INTRADAY)
        items = []
        for row in df_records(data):
            items.append(
                {
                    "time": pick(row, "flow_item_time", "time_key", "time"),
                    "in_flow": pick(row, "in_flow"),
                    "super_in_flow": pick(row, "super_in_flow"),
                    "big_in_flow": pick(row, "big_in_flow"),
                    "mid_in_flow": pick(row, "mid_in_flow"),
                    "sml_in_flow": pick(row, "sml_in_flow"),
                    "last_valid_time": pick(row, "last_valid_time"),
                }
            )
        return {"available": True, "items": items}
    except FutuError as exc:
        return {"available": False, "error": exc.message, "items": []}
    except Exception as exc:
        return {"available": False, "error": str(exc), "items": []}


def optional_company_profile(code: str) -> dict[str, Any]:
    try:
        data = get_quote_client().call("get_company_profile", code)
        items = []
        for row in df_records(data):
            items.append(
                {
                    "name": pick(row, "name"),
                    "value": pick(row, "value"),
                    "field_type": pick(row, "field_type"),
                }
            )
        return {"available": True, "items": items}
    except FutuError as exc:
        return {"available": False, "error": exc.message, "items": []}
    except Exception as exc:
        return {"available": False, "error": str(exc), "items": []}
