from __future__ import annotations

import math
from typing import Any

import pandas as pd


def json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, pd.Timestamp):
        return value.isoformat(sep=" ")
    if hasattr(value, "isoformat") and callable(value.isoformat) and not isinstance(value, (list, dict, tuple)):
        try:
            return value.isoformat()
        except Exception:
            pass
    try:
        if not isinstance(value, (list, dict, tuple, bytes)) and pd.isna(value):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    return str(value)


def df_records(data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if isinstance(data, pd.DataFrame):
        if data.empty:
            return []
        return [{str(k): json_safe(v) for k, v in row.items()} for row in data.to_dict(orient="records")]
    if isinstance(data, list):
        out: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict):
                out.append({str(k): json_safe(v) for k, v in item.items()})
        return out
    return []


def pick(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default
