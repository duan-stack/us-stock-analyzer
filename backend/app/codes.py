from __future__ import annotations

import re

NON_US_MARKETS = {
    "HK",
    "SH",
    "SZ",
    "CN",
    "SG",
    "JP",
    "AU",
    "CA",
    "MY",
    "KR",
    "TW",
    "UK",
    "GB",
    "DE",
    "FR",
    "IT",
    "IN",
    "BR",
    "TH",
    "ID",
    "PH",
    "VN",
    "NZ",
}
US_ONLY_HINT = "本系统仅支持美股，请使用如 AAPL、NVDA 或 US.MSFT"
_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")


def _valid_symbol(symbol: str) -> bool:
    return bool(symbol and _SYMBOL_RE.fullmatch(symbol))


def normalize_code(code: str) -> str:
    raw = (code or "").strip().upper().replace("-", ".")
    if not raw:
        raise ValueError("股票代码不能为空")
    if raw.startswith("US."):
        symbol = raw[3:].strip()
        if not _valid_symbol(symbol):
            raise ValueError(US_ONLY_HINT)
        return f"US.{symbol}"
    if raw.isdigit():
        raise ValueError(US_ONLY_HINT)
    if "." not in raw:
        if not _valid_symbol(raw):
            raise ValueError(US_ONLY_HINT)
        return f"US.{raw}"
    left, right = raw.split(".", 1)
    if left == "US":
        symbol = right.strip()
        if not _valid_symbol(symbol):
            raise ValueError(US_ONLY_HINT)
        return f"US.{symbol}"
    if right == "US":
        if not _valid_symbol(left):
            raise ValueError(US_ONLY_HINT)
        return f"US.{left}"
    if left in NON_US_MARKETS or right in NON_US_MARKETS:
        raise ValueError(US_ONLY_HINT)
    if right[:1].isdigit():
        raise ValueError(US_ONLY_HINT)
    if not _valid_symbol(raw):
        raise ValueError(US_ONLY_HINT)
    return f"US.{raw}"


def is_us_code(code: str) -> bool:
    try:
        return normalize_code(code).startswith("US.")
    except ValueError:
        return False


def market_of(code: str) -> str:
    return "US"


def display_symbol(code: str) -> str:
    normalized = normalize_code(code)
    return normalized.split(".", 1)[1]


def yahoo_symbol(code: str) -> str:
    return display_symbol(code).replace(".", "-")
