from __future__ import annotations

import math
from typing import Any

from app.codes import display_symbol, market_of

LOGIC_VERSION = "logic-v3"
FRAMEWORK_NAME = "四维分析"
FRAMEWORK_MARK = f"<!-- {LOGIC_VERSION} -->"

BULL_NEWS = (
    "回购",
    "超预期",
    "上调",
    "upgrade",
    "beat",
    "增长",
    "买入",
    "增持",
    "buy",
    "outperform",
    "加速",
)
BEAR_NEWS = (
    "下调",
    "不及预期",
    "downgrade",
    "miss",
    "减持",
    "调查",
    "亏损",
    "sell",
    "underperform",
    "裁员",
    "预警",
    "造假",
)


def _f(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _sma(values: list[float], window: int) -> float | None:
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    return 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))


def _stdev(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


def _ret(values: list[float], lookback: int) -> float | None:
    if len(values) <= lookback:
        return None
    start = values[-(lookback + 1)]
    end = values[-1]
    if start == 0:
        return None
    return end / start - 1.0


def _pos(price: float | None, low: float | None, high: float | None) -> float | None:
    if price is None or low is None or high is None or high <= low:
        return None
    return (price - low) / (high - low)


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(value, digits)


def _stance(score: int) -> str:
    if score >= 1:
        return "偏多"
    if score <= -1:
        return "偏空"
    return "中性"


def _fmt(value: float | None, digits: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def compute_indicators(bars: list[dict[str, Any]], snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = snapshot or {}
    closes = [c for c in (_f(b.get("close")) for b in bars) if c is not None]
    volumes = [v for v in (_f(b.get("volume")) for b in bars) if v is not None]
    last = closes[-1] if closes else _f(snapshot.get("last_price"))
    last120 = closes[-120:] if len(closes) >= 2 else closes
    logrets: list[float] = []
    window = last120[-21:] if len(last120) > 21 else last120
    for i in range(1, len(window)):
        if window[i - 1] > 0:
            logrets.append(math.log(window[i] / window[i - 1]))
    vol = _stdev(logrets)
    return {
        "last_close": last,
        "ma5": _sma(closes, 5),
        "ma10": _sma(closes, 10),
        "ma20": _sma(closes, 20),
        "ma60": _sma(closes, 60),
        "rsi14": _rsi(closes, 14),
        "return_5d": _ret(closes, 5),
        "return_20d": _ret(closes, 20),
        "return_60d": _ret(closes, 60),
        "return_120d": _ret(closes, 120) if len(closes) > 120 else (_ret(closes, max(len(closes) - 1, 1)) if len(closes) >= 2 else None),
        "volatility_ann": vol * math.sqrt(252) if vol is not None else None,
        "high_120d": max(last120) if last120 else None,
        "low_120d": min(last120) if last120 else None,
        "range_120d": _pos(last, min(last120) if last120 else None, max(last120) if last120 else None),
        "vol_ratio": (
            volumes[-1] / (_sma(volumes, 20) or 0)
            if volumes and _sma(volumes, 20)
            else None
        ),
        "bar_count": len(closes),
    }


def _trend_dimension(ind: dict[str, Any]) -> dict[str, Any]:
    price = _f(ind.get("last_close"))
    ma5, ma10, ma20, ma60 = _f(ind.get("ma5")), _f(ind.get("ma10")), _f(ind.get("ma20")), _f(ind.get("ma60"))
    evidence: list[str] = []
    score = 0
    if price is None or ma20 is None:
        return {
            "id": "trend",
            "title": "趋势结构",
            "score": 0,
            "stance": "数据不足",
            "summary": "日线样本不足，无法判断均线结构。",
            "evidence": ["缺少收盘价或 MA20"],
        }
    if price >= ma20:
        score += 1
        evidence.append(f"收盘 {_fmt(price)} 站上 MA20 {_fmt(ma20)}")
    else:
        score -= 1
        evidence.append(f"收盘 {_fmt(price)} 跌破 MA20 {_fmt(ma20)}")
    if ma20 is not None and ma60 is not None:
        if ma20 >= ma60:
            score += 1
            evidence.append(f"MA20 {_fmt(ma20)} 高于 MA60 {_fmt(ma60)}，中期方向向上")
        else:
            score -= 1
            evidence.append(f"MA20 {_fmt(ma20)} 低于 MA60 {_fmt(ma60)}，中期方向向下")
    if ma5 is not None and ma10 is not None and ma20 is not None:
        if ma5 >= ma10 >= ma20:
            evidence.append("MA5≥MA10≥MA20，短线多头排列")
        elif ma5 <= ma10 <= ma20:
            evidence.append("MA5≤MA10≤MA20，短线空头排列")
        else:
            evidence.append("短线均线纠缠，方向尚未对齐")
    score = max(-2, min(2, score))
    if score >= 2:
        summary = "中期均线向上且价格在 MA20 上方，趋势结构偏多。"
    elif score <= -2:
        summary = "中期均线向下且价格在 MA20 下方，趋势结构偏空。"
    elif score > 0:
        summary = "价格强于短均线，但中期结构尚未完全确认。"
    elif score < 0:
        summary = "价格弱于短均线，中期尚未转为明确空头或仍在修复。"
    else:
        summary = "多空均线信号对冲，趋势结构中性。"
    return {
        "id": "trend",
        "title": "趋势结构",
        "score": score,
        "stance": _stance(score),
        "summary": summary,
        "evidence": evidence,
    }


def _position_dimension(ind: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    price = _f(ind.get("last_close"))
    rsi = _f(ind.get("rsi14"))
    loc = _f(ind.get("range_120d"))
    loc52 = _pos(price, _f(snapshot.get("lowest52weeks_price")), _f(snapshot.get("highest52weeks_price")))
    ret20 = _f(ind.get("return_20d"))
    evidence: list[str] = []
    score = 0
    if loc is not None:
        evidence.append(f"近 120 日区间位置 {_pct(loc)}")
        if loc >= 0.8:
            evidence.append("处于近 120 日高位区：趋势若成立则是强势，否则是拥挤")
        elif loc <= 0.2:
            score += 1
            evidence.append("处于近 120 日低位区，位置上具备修复弹性")
        else:
            evidence.append("处于近 120 日中轴附近")
    if loc52 is not None:
        evidence.append(f"52 周区间位置 {_pct(loc52)}")
    if rsi is not None:
        evidence.append(f"RSI14 {_fmt(rsi, 1)}")
        if rsi >= 70:
            score -= 1
            evidence.append("RSI 进入超买区，动量过热")
        elif rsi <= 30:
            score += 1
            evidence.append("RSI 进入超卖区，短线有修复动能")
        elif rsi >= 55:
            score += 1
            evidence.append("RSI 位于多头动量区")
        elif rsi <= 45:
            score -= 1
            evidence.append("RSI 位于空头动量区")
        else:
            evidence.append("RSI 中性")
    if ret20 is not None:
        evidence.append(f"近 20 日收益 {_pct(ret20)}")
        if ret20 >= 0.08:
            score += 1
        elif ret20 <= -0.08:
            score -= 1
    if not evidence:
        return {
            "id": "position",
            "title": "位置与动量",
            "score": 0,
            "stance": "数据不足",
            "summary": "缺少区间或 RSI，无法判断位置。",
            "evidence": [],
        }
    score = max(-2, min(2, score))
    if score >= 1:
        summary = "动量仍偏强。" + ("当前已在高位区，节奏上不宜追涨杀跌。" if (loc or 0) >= 0.8 else "位置与动量共同指向偏多。")
    elif score <= -1:
        summary = "动量转弱或超买回落，位置上需要防守。"
    else:
        summary = "区间位置与动量对冲，尚未形成一边倒。"
    return {
        "id": "position",
        "title": "位置与动量",
        "score": score,
        "stance": _stance(score),
        "summary": summary,
        "evidence": evidence,
        "range_120d": _round(loc, 3),
        "range_52w": _round(loc52, 3),
    }


def _risk_dimension(ind: dict[str, Any], drawdown: dict[str, Any]) -> dict[str, Any]:
    current = _f(drawdown.get("current_drawdown"))
    max_dd = _f(drawdown.get("max_drawdown"))
    vol = _f(ind.get("volatility_ann"))
    underwater = drawdown.get("underwater_days")
    vol_ratio = _f(ind.get("vol_ratio"))
    evidence: list[str] = []
    score = 0
    if current is not None:
        evidence.append(f"当前回撤 {_pct(current)}")
        if current <= -0.25:
            score -= 2
            evidence.append("当前回撤超过 25%，风险释放尚未结束或处于深水区")
        elif current <= -0.12:
            score -= 1
            evidence.append("当前回撤超过 12%，属于中等压力")
        elif current >= -0.03:
            score += 1
            evidence.append("接近阶段高点，回撤压力轻，但追高容错低")
        else:
            evidence.append("回撤幅度尚可")
    if max_dd is not None:
        evidence.append(f"样本最大回撤 {_pct(max_dd)}")
        if current is not None and max_dd < -0.01 and current <= max_dd * 0.85:
            evidence.append("当前回撤接近样本最大回撤，价格仍在历史压力带")
    if vol is not None:
        evidence.append(f"近 20 日波动年化 {_pct(vol)}")
        if vol >= 0.45:
            score -= 1
            evidence.append("波动偏高，同样回撤下亏损更快")
        elif vol <= 0.18:
            evidence.append("波动相对温和")
    if underwater is not None:
        evidence.append(f"水下交易日 {underwater}")
    if vol_ratio is not None:
        evidence.append(f"最新成交量 / 20 日均量 {_fmt(vol_ratio, 2)}")
        if vol_ratio >= 1.8:
            evidence.append("放量，方向确认或恐慌都可能被放大")
        elif vol_ratio <= 0.6:
            evidence.append("缩量，突破或下跌的可信度下降")
    score = max(-2, min(2, score))
    if score <= -1:
        summary = "回撤或波动显示风险偏高，仓位与预期都要降一档。"
    elif score >= 1:
        summary = "回撤压力轻，风险主要来自高位拥挤而非深跌。"
    else:
        summary = "回撤与波动处于可观察区间，风险中性。"
    return {
        "id": "risk",
        "title": "回撤与风险",
        "score": score,
        "stance": _stance(score),
        "summary": summary,
        "evidence": evidence,
    }


def _value_dimension(snapshot: dict[str, Any], news_items: list[dict[str, Any]]) -> dict[str, Any]:
    pe = _f(snapshot.get("pe_ttm_ratio")) or _f(snapshot.get("pe_ratio"))
    pb = _f(snapshot.get("pb_ratio"))
    evidence: list[str] = []
    score = 0
    if pe is None:
        evidence.append("无有效 PE（可能为亏损、ETF 或权限不足），估值不作强判断")
    elif pe < 0:
        score -= 1
        evidence.append(f"PE {_fmt(pe, 1)} 为负，盈利尚未转正或口径特殊")
    elif pe >= 50:
        score -= 1
        evidence.append(f"PE {_fmt(pe, 1)} 偏高，需要增长叙事才能支撑")
    elif pe <= 12:
        score += 1
        evidence.append(f"PE {_fmt(pe, 1)} 偏低，估值有安全垫，但可能有基本面折价")
    else:
        evidence.append(f"PE {_fmt(pe, 1)} 处于常见区间")
    if pb is not None and pb > 0:
        evidence.append(f"PB {_fmt(pb, 2)}")
        if pb >= 10:
            evidence.append("PB 很高，价格更多折现成长而非净资产")
        elif pb <= 1:
            score += 1
            evidence.append("PB 低于 1，资产价格偏低或盈利能力存疑")
    bull = 0
    bear = 0
    for item in news_items[:12]:
        title = str(item.get("title") or "").lower()
        if any(k.lower() in title for k in BULL_NEWS):
            bull += 1
        if any(k.lower() in title for k in BEAR_NEWS):
            bear += 1
    if news_items:
        evidence.append(f"近条资讯中偏多关键词 {bull} 条、偏空关键词 {bear} 条")
        if bull - bear >= 2:
            score += 1
        elif bear - bull >= 2:
            score -= 1
        else:
            evidence.append("资讯情绪未形成单边")
    else:
        evidence.append("暂无可用资讯，事件维度中性")
    score = max(-2, min(2, score))
    if score >= 1:
        summary = "估值或事件提供正向支持，但仍不能替代趋势确认。"
    elif score <= -1:
        summary = "估值偏贵或事件偏空，上涨需要更强的趋势与动量。"
    else:
        summary = "估值与事件没有一边倒，更多作为趋势的过滤器。"
    return {
        "id": "value",
        "title": "估值与事件",
        "score": score,
        "stance": _stance(score),
        "summary": summary,
        "evidence": evidence,
    }


def _levels(ind: dict[str, Any], snapshot: dict[str, Any], bias: str) -> dict[str, Any]:
    price = _f(ind.get("last_close"))
    candidates = [
        ("MA5", _f(ind.get("ma5"))),
        ("MA10", _f(ind.get("ma10"))),
        ("MA20", _f(ind.get("ma20"))),
        ("MA60", _f(ind.get("ma60"))),
        ("120日低", _f(ind.get("low_120d"))),
        ("120日高", _f(ind.get("high_120d"))),
        ("52周低", _f(snapshot.get("lowest52weeks_price"))),
        ("52周高", _f(snapshot.get("highest52weeks_price"))),
    ]
    supports: list[dict[str, Any]] = []
    resistances: list[dict[str, Any]] = []
    if price is not None:
        for name, value in candidates:
            if value is None:
                continue
            item = {"name": name, "price": _round(value, 4)}
            if value < price * 0.998:
                supports.append(item)
            elif value > price * 1.002:
                resistances.append(item)
        supports.sort(key=lambda x: abs(price - float(x["price"])))
        resistances.sort(key=lambda x: abs(float(x["price"]) - price))
    ma20 = _f(ind.get("ma20"))
    ma60 = _f(ind.get("ma60"))
    if bias == "偏多":
        invalid = f"若日线收盘跌破 MA20（{_fmt(ma20)}）且不能迅速收回，偏多结构失效"
    elif bias == "偏空":
        invalid = f"若日线收盘重新站上 MA20（{_fmt(ma20)}）并守住 MA60（{_fmt(ma60)}），偏空结构需要重新评估"
    else:
        invalid = f"等待收盘稳定站上或跌破 MA20（{_fmt(ma20)}）再确认方向"
    return {
        "last_close": _round(price, 4),
        "supports": supports[:4],
        "resistances": resistances[:4],
        "invalidation": invalid,
    }


def _verdict(dimensions: list[dict[str, Any]], ind: dict[str, Any]) -> dict[str, Any]:
    total = sum(int(d.get("score") or 0) for d in dimensions)
    trend = next((d for d in dimensions if d.get("id") == "trend"), {})
    risk = next((d for d in dimensions if d.get("id") == "risk"), {})
    trend_score = int(trend.get("score") or 0)
    risk_score = int(risk.get("score") or 0)
    if total >= 2 and trend_score >= 1:
        bias = "偏多"
    elif total <= -2 and trend_score <= -1:
        bias = "偏空"
    else:
        bias = "中性"
    if bias == "偏多" and risk_score <= -2:
        bias = "中性"
    abs_total = abs(total)
    missing = any(d.get("stance") == "数据不足" for d in dimensions)
    if missing or abs_total <= 1:
        confidence = "低"
    elif abs_total >= 5:
        confidence = "高"
    else:
        confidence = "中"
    trend_s = trend.get("summary") or "趋势待确认"
    if bias == "偏多":
        one_liner = f"四维合计 {total} 分，偏向多头；{trend_s}"
    elif bias == "偏空":
        one_liner = f"四维合计 {total} 分，偏向空头；{trend_s}"
    else:
        one_liner = f"四维合计 {total} 分，方向不明或信号对冲，先观察再定性。"
    return {
        "bias": bias,
        "score": total,
        "confidence": confidence,
        "one_liner": one_liner,
    }


def _watchlist(bias: str, levels: dict[str, Any], ind: dict[str, Any]) -> list[str]:
    ma20 = _fmt(_f(ind.get("ma20")))
    rsi = _f(ind.get("rsi14"))
    items = [
        f"盯日线收盘与 MA20（{ma20}）的关系，这是本框架的方向开关",
        levels.get("invalidation") or "等待结构确认",
    ]
    if rsi is not None and rsi >= 70:
        items.append("RSI 超买，若放量滞涨，优先当成减仓/观望信号而非继续加码")
    if rsi is not None and rsi <= 30:
        items.append("RSI 超卖，反弹需要放量站回 MA20 才能升格为趋势修复")
    if bias == "中性":
        items.append("在失效价被打穿或站稳之前，不把震荡当成单边")
    return items[:5]


def build_logic(
    code: str,
    snapshot: dict[str, Any] | None,
    bars: list[dict[str, Any]],
    drawdown: dict[str, Any] | None,
    news_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    snapshot = snapshot or {}
    drawdown = {k: v for k, v in (drawdown or {}).items() if k != "series"}
    news_items = news_items or []
    ind = compute_indicators(bars, snapshot)
    dimensions = [
        _trend_dimension(ind),
        _position_dimension(ind, snapshot),
        _risk_dimension(ind, drawdown),
        _value_dimension(snapshot, news_items),
    ]
    verdict = _verdict(dimensions, ind)
    levels = _levels(ind, snapshot, verdict["bias"])
    return {
        "version": LOGIC_VERSION,
        "framework": FRAMEWORK_NAME,
        "framework_note": "趋势结构决定方向，位置与动量决定节奏，回撤与风险决定仓位弹性，估值与事件只做过滤器。四维冲突时，以趋势为先、风险一票否决追高。",
        "code": code,
        "market": market_of(code),
        "symbol": display_symbol(code),
        "name": snapshot.get("name") or "",
        "verdict": verdict,
        "dimensions": dimensions,
        "levels": levels,
        "watchlist": _watchlist(verdict["bias"], levels, ind),
        "indicators": {k: _round(v, 6) if isinstance(v, float) else v for k, v in ind.items()},
        "disclaimer": "以上为规则化研究框架，仅供分析参考，不构成投资建议。",
    }


def logic_for_prompt(logic: dict[str, Any]) -> str:
    verdict = logic.get("verdict") or {}
    lines = [
        f"框架：{logic.get('framework')}（{logic.get('version')}）",
        f"使用说明：{logic.get('framework_note')}",
        f"裁定：{verdict.get('bias')}｜总分 {verdict.get('score')}｜把握 {verdict.get('confidence')}",
        f"一句话：{verdict.get('one_liner')}",
        "",
        "四维明细：",
    ]
    for dim in logic.get("dimensions") or []:
        lines.append(f"- {dim.get('title')}｜{dim.get('stance')}｜{dim.get('score')}分｜{dim.get('summary')}")
        for ev in dim.get("evidence") or []:
            lines.append(f"    · {ev}")
    levels = logic.get("levels") or {}
    sup = "、".join(f"{x.get('name')} {x.get('price')}" for x in (levels.get("supports") or [])[:3]) or "无"
    res = "、".join(f"{x.get('name')} {x.get('price')}" for x in (levels.get("resistances") or [])[:3]) or "无"
    lines += [
        "",
        f"支撑：{sup}",
        f"压力：{res}",
        f"失效条件：{levels.get('invalidation')}",
        "观察清单：",
    ]
    for item in logic.get("watchlist") or []:
        lines.append(f"- {item}")
    return "\n".join(lines)
