from __future__ import annotations

import re
from typing import Any

from app.codes import normalize_code

# Common OTC / pink-sheet / obscure ADR patterns in Futu US movers.
_BAD_NAME = re.compile(
    r"UNSP(?:ON)?(?:\s+ADS|\s+ADR)|ADS\s+EACH\s+REP|ADR\s+EACH\s+REP|ORD\s+SHS|PINK|OTC",
    re.I,
)
_MAIN_ETF = {
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "VTI",
    "VOO",
    "IVV",
    "ARKK",
    "XLF",
    "XLK",
    "XLE",
    "SOXX",
    "SMH",
    "TQQQ",
    "SQQQ",
    "SPXU",
    "UVXY",
}


def _symbol(code: str | None) -> str:
    raw = str(code or "").strip().upper()
    if not raw:
        return ""
    try:
        return normalize_code(raw).removeprefix("US.")
    except ValueError:
        if raw.startswith("US."):
            return raw[3:]
        return raw


def is_mainstream_us_listing(code: str | None, name: str | None = None) -> bool:
    symbol = _symbol(code)
    if not symbol:
        return False
    title = str(name or "")
    if _BAD_NAME.search(title):
        return False
    if symbol in _MAIN_ETF:
        return True
    # Prefer ordinary tickers / class shares: AAPL, BRK.B, BF.A
    if re.fullmatch(r"[A-Z]{1,4}(?:\.[A-Z])?", symbol):
        return True
    # 5-letter endings common on movers boards for ADRs / warrants / units.
    if re.fullmatch(r"[A-Z]{5}", symbol) and symbol[-1] in {"Y", "F", "Z", "W", "U"}:
        return False
    if re.fullmatch(r"[A-Z]{5}", symbol):
        return True
    return False


def filter_board_items(items: list[dict[str, Any]], limit: int = 10) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for row in items:
        if is_mainstream_us_listing(row.get("code"), row.get("name")):
            kept.append(row)
        if len(kept) >= limit:
            break
    return kept
