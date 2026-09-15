from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.codes import NON_US_MARKETS, normalize_code
from app.config import get_settings
from app.db import get_report
from app.futu_client import FutuError, get_quote_client
from app.services.ai_report import analyze_stock, generate_report
from app.services.analysis import FRAMEWORK_MARK
from app.services.drawdown import compute_drawdown
from app.services.kline import fetch_history_kline, normalize_ktype
from app.services.news import optional_capital_flow, optional_company_profile, optional_owner_plate, search_news
from app.services.serialize import df_records, pick
from app.services.snapshot import get_snapshots

router = APIRouter(tags=["stocks"])


class ReportIn(BaseModel):
    force: bool = False


def _code(code: str) -> str:
    try:
        return normalize_code(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _search_item(code: str, name: str | None = "", sec_type: str | None = None, is_watched: object = None) -> dict:
    return {
        "code": code,
        "name": name or "",
        "market": "US",
        "sec_type": sec_type,
        "is_watched": is_watched,
    }


@router.get("/api/stocks/search")
def search_stocks(q: str = "") -> dict:
    keyword = q.strip()
    if not keyword:
        return {"items": []}
    if keyword.replace(".", "").isdigit():
        return {"items": []}

    items: list[dict] = []
    seen: set[str] = set()
    needle = keyword.upper().removeprefix("US.").replace("-", ".")

    try:
        exact = normalize_code(keyword)
    except ValueError:
        exact = None
    if exact:
        items.append(_search_item(exact))
        seen.add(exact)

    try:
        data = get_quote_client().call("get_search_quote", keyword, 30)
    except FutuError:
        return {"items": items}

    for row in df_records(data):
        raw = pick(row, "code")
        market = str(pick(row, "market") or "").upper()
        if market and market != "US":
            continue
        try:
            code = normalize_code(str(raw)) if raw else ""
        except ValueError:
            continue
        if not code.startswith("US."):
            continue
        if "." in str(raw or "") and not str(raw).upper().startswith("US."):
            left = str(raw).split(".", 1)[0].upper()
            if left in NON_US_MARKETS or str(raw).split(".", 1)[-1][:1].isdigit():
                continue
        name = pick(row, "name")
        sec_type = str(pick(row, "sec_type") or "").upper()
        if sec_type and sec_type not in {"STOCK", "ETF"}:
            continue
        if code in seen:
            for item in items:
                if item["code"] == code:
                    if name and not item.get("name"):
                        item["name"] = name
                    item["sec_type"] = pick(row, "sec_type")
                    item["is_watched"] = pick(row, "is_watched")
            continue
        items.append(_search_item(code, name, pick(row, "sec_type"), pick(row, "is_watched")))
        seen.add(code)

    def _search_rank(item: dict) -> tuple[int, str]:
        symbol = str(item.get("code") or "").removeprefix("US.")
        name = str(item.get("name") or "").upper()
        if symbol == needle or item.get("code") == f"US.{needle}":
            return (0, symbol)
        if symbol.startswith(needle) or needle in name:
            return (1, symbol)
        return (2, symbol)

    items.sort(key=_search_rank)
    return {"items": items[:20]}


@router.get("/api/stocks/{code}/snapshot")
def stock_snapshot(code: str) -> dict:
    normalized = _code(code)
    snaps = get_snapshots([normalized])
    if not snaps:
        raise FutuError(f"未获取到 {normalized} 的快照")
    return snaps[0]


@router.get("/api/stocks/{code}/kline")
def stock_kline(code: str, ktype: str = "K_DAY") -> dict:
    normalized = _code(code)
    return fetch_history_kline(normalized, normalize_ktype(ktype))


@router.get("/api/stocks/{code}/drawdown")
def stock_drawdown(code: str) -> dict:
    normalized = _code(code)
    kline = fetch_history_kline(normalized, "K_DAY")
    metrics = compute_drawdown(kline.get("bars") or [])
    return {"code": normalized, "ktype": "K_DAY", "cached": kline.get("cached"), **metrics}


@router.get("/api/stocks/{code}/news")
def stock_news(code: str) -> dict:
    normalized = _code(code)
    name = ""
    try:
        snaps = get_snapshots([normalized])
        if snaps:
            name = str(snaps[0].get("name") or "")
    except FutuError:
        name = ""
    return search_news(normalized, name, max_count=20)


@router.get("/api/stocks/{code}/capital-flow")
def stock_capital_flow(code: str) -> dict:
    return optional_capital_flow(_code(code))


@router.get("/api/stocks/{code}/plates")
def stock_plates(code: str) -> dict:
    return optional_owner_plate(_code(code))


@router.get("/api/stocks/{code}/profile")
def stock_profile(code: str) -> dict:
    return optional_company_profile(_code(code))


@router.get("/api/stocks/{code}/analysis")
def stock_analysis(code: str) -> dict:
    normalized = _code(code)
    try:
        return analyze_stock(normalized)
    except FutuError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc


@router.get("/api/stocks/{code}/ai-report")
def get_ai_report(code: str) -> dict:
    normalized = _code(code)
    settings = get_settings()
    cached = get_report(normalized, settings.report_cache_ttl_sec)
    if not cached or FRAMEWORK_MARK not in str(cached.get("markdown") or ""):
        raise HTTPException(status_code=404, detail="尚未生成报告")
    return {**cached, "cached": not cached.get("expired")}


@router.post("/api/stocks/{code}/ai-report")
def post_ai_report(code: str, body: ReportIn = ReportIn()) -> dict:
    normalized = _code(code)
    force = bool(body.force)
    try:
        return generate_report(normalized, force=force)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
