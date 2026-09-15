from __future__ import annotations

from typing import Any

from app.codes import normalize_code
from app.futu_client import get_quote_client
from app.services.serialize import df_records, pick


def _num(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def shape_snapshot(row: dict[str, Any]) -> dict[str, Any]:
    last_price = _num(pick(row, "last_price"))
    prev_close = _num(pick(row, "prev_close_price"))
    change_val = None
    change_rate = _num(pick(row, "change_rate"))
    if last_price is not None and prev_close not in (None, 0):
        change_val = last_price - prev_close
        if change_rate is None:
            change_rate = (last_price / prev_close - 1.0) * 100.0
    return {
        "code": pick(row, "code"),
        "name": pick(row, "name"),
        "update_time": pick(row, "update_time"),
        "last_price": last_price,
        "open_price": _num(pick(row, "open_price")),
        "high_price": _num(pick(row, "high_price")),
        "low_price": _num(pick(row, "low_price")),
        "prev_close_price": prev_close,
        "change_val": change_val,
        "change_rate": change_rate,
        "volume": _num(pick(row, "volume")),
        "turnover": _num(pick(row, "turnover")),
        "turnover_rate": _num(pick(row, "turnover_rate")),
        "amplitude": _num(pick(row, "amplitude")),
        "pe_ratio": _num(pick(row, "pe_ratio")),
        "pe_ttm_ratio": _num(pick(row, "pe_ttm_ratio")),
        "pb_ratio": _num(pick(row, "pb_ratio")),
        "total_market_val": _num(pick(row, "total_market_val")),
        "highest52weeks_price": _num(pick(row, "highest52weeks_price")),
        "lowest52weeks_price": _num(pick(row, "lowest52weeks_price")),
        "suspension": pick(row, "suspension"),
        "sec_status": pick(row, "sec_status"),
        "pre_price": _num(pick(row, "pre_price")),
        "pre_change_rate": _num(pick(row, "pre_change_rate")),
        "after_price": _num(pick(row, "after_price")),
        "after_change_rate": _num(pick(row, "after_change_rate")),
    }


def get_snapshots(codes: list[str]) -> list[dict[str, Any]]:
    quoted = []
    for code in codes:
        try:
            quoted.append(normalize_code(code))
        except ValueError:
            continue
    if not quoted:
        return []
    data = get_quote_client().call("get_market_snapshot", quoted)
    return [shape_snapshot(row) for row in df_records(data)]


def shape_rank(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": pick(row, "code", "security"),
        "name": pick(row, "name"),
        "last_price": pick(row, "last_price", "cur_price", "price"),
        "change_rate": pick(row, "change_rate", "change_ratio"),
        "turnover": pick(row, "turnover"),
        "volume": pick(row, "volume"),
        "pe_ratio": pick(row, "pe_ratio", "pe_ttm", "pe_ttm_ratio"),
    }


def shape_hot(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": pick(row, "security", "code"),
        "name": pick(row, "name"),
        "average_heat": pick(row, "average_heat"),
        "trade_heat": pick(row, "trade_heat"),
        "search_heat": pick(row, "search_heat"),
        "news_heat": pick(row, "news_heat"),
        "news_type": pick(row, "news_type"),
        "news_title": pick(row, "news_title"),
        "news_url": pick(row, "news_url"),
    }
