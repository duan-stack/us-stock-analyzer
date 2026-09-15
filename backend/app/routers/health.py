from fastapi import APIRouter

from app.config import get_settings
from app.futu_client import get_quote_client
from app.services.us_session import us_equity_session

router = APIRouter(tags=["health"])

MARKET_STATE_ZH = {
    "NONE": "未知",
    "AUCTION": "竞价",
    "WAITING_OPEN": "等待开盘",
    "MORNING": "盘中",
    "REST": "休市",
    "AFTERNOON": "盘中",
    "CLOSED": "已收盘",
    "PRE_MARKET_BEGIN": "盘前",
    "PRE_MARKET_END": "盘前结束",
    "AFTER_HOURS_BEGIN": "盘后",
    "AFTER_HOURS_END": "盘后结束",
    "NIGHT_OPEN": "夜盘",
    "NIGHT_END": "夜盘结束",
    "FUTURE_DAY_OPEN": "期货日盘",
    "FUTURE_DAY_BREAK": "期货日盘休市",
    "FUTURE_DAY_CLOSE": "期货日盘收市",
    "FUTURE_DAY_WAIT_OPEN": "期货等待开盘",
    "HK_CAS": "收市竞价",
    "FUTURE_NIGHT_WAIT": "期货夜盘等待",
    "FUTURE_OPEN": "期货开盘",
    "FUTURE_BREAK_OVER": "期货休息结束",
    "FUTURE_CLOSE": "期货收市",
    "NIGHT": "夜盘",
}


def market_state_label(state: str | None) -> str | None:
    if not state:
        return None
    return MARKET_STATE_ZH.get(str(state).upper(), str(state))


market_us_label = market_state_label


@router.get("/api/health")
def health() -> dict:
    settings = get_settings()
    client = get_quote_client()
    ok, state, error = client.ping()
    market_us = None
    qot_logined = None
    if isinstance(state, dict):
        market_us = state.get("market_us")
        qot_logined = state.get("qot_logined")
    session = us_equity_session()
    return {
        "opend": {
            "connected": ok,
            "host": settings.futu_host,
            "port": settings.futu_port,
            "qot_logined": qot_logined,
            "market_us": market_us,
            "market_us_label": market_state_label(str(market_us) if market_us is not None else None),
            "error": None if ok else (error or "请启动 FutuOpenD"),
            "state": state,
        },
        "us_session": session,
        "deepseek": {
            "configured": bool(settings.deepseek_api_key.strip()),
            "model": settings.deepseek_model,
            "base_url": settings.deepseek_base_url,
        },
    }


@router.get("/api/settings")
def settings_view() -> dict:
    settings = get_settings()
    return {
        "futu_host": settings.futu_host,
        "futu_port": settings.futu_port,
        "deepseek_configured": bool(settings.deepseek_api_key.strip()),
        "deepseek_model": settings.deepseek_model,
        "deepseek_base_url": settings.deepseek_base_url,
        "report_cache_hours": settings.report_cache_ttl_sec / 3600,
    }
