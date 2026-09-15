from __future__ import annotations

from typing import Any


def _f(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def compute_drawdown(bars: list[dict[str, Any]]) -> dict[str, Any]:
    series: list[dict[str, Any]] = []
    peak = None
    peak_time = None
    max_dd = 0.0
    max_dd_start = None
    max_dd_end = None
    max_dd_peak_time = None
    underwater_days = 0
    trough_close = None
    trough_time = None
    first_close = None
    last_close = None
    last_time = None

    for bar in bars:
        close = _f(bar.get("close"))
        t = bar.get("time")
        if close is None:
            continue
        if first_close is None:
            first_close = close
        last_close = close
        last_time = t
        if trough_close is None or close < trough_close:
            trough_close = close
            trough_time = t
        if peak is None or close >= peak:
            peak = close
            peak_time = t
        dd = close / peak - 1.0 if peak else 0.0
        if dd < 0:
            underwater_days += 1
        if dd < max_dd:
            max_dd = dd
            max_dd_start = peak_time
            max_dd_end = t
            max_dd_peak_time = peak_time
        series.append(
            {
                "time": t,
                "close": close,
                "peak": peak,
                "drawdown": dd,
            }
        )

    current = series[-1]["drawdown"] if series else 0.0
    period_return = (last_close / first_close - 1.0) if first_close and last_close else None
    rebound = (last_close / trough_close - 1.0) if last_close and trough_close else None

    return {
        "current_drawdown": current,
        "max_drawdown": max_dd,
        "max_drawdown_start": max_dd_start,
        "max_drawdown_end": max_dd_end,
        "max_drawdown_peak": max_dd_peak_time,
        "underwater_days": underwater_days,
        "period_return": period_return,
        "rebound_from_trough": rebound,
        "trough_date": trough_time,
        "trough_close": trough_close,
        "last_close": last_close,
        "last_time": last_time,
        "bar_count": len(series),
        "series": series,
    }
