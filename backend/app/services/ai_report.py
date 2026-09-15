from __future__ import annotations

from typing import Any

import httpx

from app.config import get_settings
from app.db import get_report, save_report
from app.futu_client import FutuError
from app.services.analysis import FRAMEWORK_MARK, FRAMEWORK_NAME, build_logic, logic_for_prompt
from app.services.drawdown import compute_drawdown
from app.services.kline import fetch_history_kline
from app.services.news import search_news
from app.services.serialize import pick
from app.services.snapshot import get_snapshots


def _pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def build_context(code: str, include_news: bool = True) -> dict[str, Any]:
    snaps = get_snapshots([code])
    snapshot = snaps[0] if snaps else {}
    kline = fetch_history_kline(code, "K_DAY")
    bars = kline.get("bars") or []
    dd = compute_drawdown(bars)
    news_items: list[dict[str, Any]] = []
    if include_news:
        try:
            news = search_news(code, str(snapshot.get("name") or ""), max_count=10)
            news_items = news.get("items") or []
        except Exception:
            news_items = []
    logic = build_logic(code, snapshot, bars, dd, news_items)
    return {
        "code": code,
        "snapshot": snapshot,
        "indicators": logic.get("indicators") or {},
        "drawdown": {k: v for k, v in dd.items() if k != "series"},
        "news_titles": [
            {
                "title": pick(item, "title"),
                "source": pick(item, "source"),
                "publish_time": pick(item, "publish_time"),
            }
            for item in news_items[:10]
        ],
        "logic": logic,
    }


def analyze_stock(code: str) -> dict[str, Any]:
    return build_context(code, include_news=False)["logic"]


def _prompt(ctx: dict[str, Any]) -> str:
    snap = ctx.get("snapshot") or {}
    ind = ctx.get("indicators") or {}
    dd = ctx.get("drawdown") or {}
    logic = ctx.get("logic") or {}
    news_lines = "\n".join(
        f"- {n.get('publish_time') or ''} | {n.get('source') or ''} | {n.get('title') or ''}"
        for n in ctx.get("news_titles") or []
    ) or "- （暂无资讯）"
    return f"""你必须严格按照【{FRAMEWORK_NAME}】已经给出的裁定写作，不得另起一套多空结论。

报告用简体中文 Markdown，必须且只能使用下面六个二级标题：

## 分析结论
## 1. 趋势结构
## 2. 位置与动量
## 3. 回撤与风险
## 4. 估值与事件
## 5. 关键价位与观察清单

写作规则：
1. 「分析结论」第一句必须复述裁定的偏向、总分、把握，并引用一句话结论。不得改口。
2. 第 1–4 节分别对应四维：先写该维的 stance 与 score，再解释 evidence，禁止编造未提供的数字。
3. 趋势冲突时以趋势为先；若风险维为明显偏空，必须写明不能追高。
4. 第 5 节必须列出支撑、压力、失效条件，并复述观察清单。
5. 全文最后一句必须是：以上内容仅供研究参考，不构成投资建议。
6. 不要给目标价、仓位百分比或下单指令。

【四维裁定】
{logic_for_prompt(logic)}

【标的】{ctx.get('code')} {snap.get('name') or ''}
【快照】现价={snap.get('last_price')} 昨收={snap.get('prev_close_price')} 涨跌幅={snap.get('change_rate')}% 开={snap.get('open_price')} 高={snap.get('high_price')} 低={snap.get('low_price')} 成交额={snap.get('turnover')} PE={snap.get('pe_ratio')} PE_TTM={snap.get('pe_ttm_ratio')} PB={snap.get('pb_ratio')} 市值={snap.get('total_market_val')} 52周高={snap.get('highest52weeks_price')} 52周低={snap.get('lowest52weeks_price')}
【技术】MA5={ind.get('ma5')} MA10={ind.get('ma10')} MA20={ind.get('ma20')} MA60={ind.get('ma60')} RSI14={ind.get('rsi14')} 5日={_pct(ind.get('return_5d'))} 20日={_pct(ind.get('return_20d'))} 60日={_pct(ind.get('return_60d'))} 120日={_pct(ind.get('return_120d'))} 波动年化={_pct(ind.get('volatility_ann'))} 120日高={ind.get('high_120d')} 120日低={ind.get('low_120d')} 量比={ind.get('vol_ratio')}
【回撤】当前回撤={_pct(dd.get('current_drawdown'))} 最大回撤={_pct(dd.get('max_drawdown'))} 最大回撤起={dd.get('max_drawdown_start')} 最大回撤止={dd.get('max_drawdown_end')} 水下天数={dd.get('underwater_days')} 区间收益={_pct(dd.get('period_return'))} 低点反弹={_pct(dd.get('rebound_from_trough'))} 低点日={dd.get('trough_date')}
【资讯】
{news_lines}
"""


def generate_report(code: str, force: bool = False) -> dict[str, Any]:
    settings = get_settings()
    if not force:
        cached = get_report(code, settings.report_cache_ttl_sec)
        if cached and not cached.get("expired") and FRAMEWORK_MARK in str(cached.get("markdown") or ""):
            return {**cached, "cached": True}

    if not settings.deepseek_api_key.strip():
        raise RuntimeError("未配置 DEEPSEEK_API_KEY，请在项目根目录 .env 中填写")

    ctx = build_context(code)
    base = settings.deepseek_base_url.rstrip("/")
    url = f"{base}/chat/completions" if not base.endswith("/chat/completions") else base
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"你是{FRAMEWORK_NAME}研究助理，只研究美股。你只解释已经算好的规则化结论，"
                    "不推翻框架、不编造财报数字、不给下单建议。使用简体中文 Markdown。"
                ),
            },
            {"role": "user", "content": _prompt(ctx)},
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(url, json=payload, headers=headers)
        try:
            body = resp.json()
        except Exception as exc:
            raise RuntimeError(f"DeepSeek 返回无法解析: HTTP {resp.status_code}") from exc
        if resp.status_code >= 400:
            detail = body.get("error", body) if isinstance(body, dict) else body
            raise RuntimeError(f"DeepSeek 调用失败: {detail}")
        markdown = (
            (((body.get("choices") or [{}])[0].get("message") or {}).get("content"))
            if isinstance(body, dict)
            else None
        )
        if not markdown:
            raise RuntimeError("DeepSeek 未返回有效内容")

    saved = save_report(code, f"{FRAMEWORK_MARK}\n{markdown}")
    saved["logic"] = ctx.get("logic")
    saved["cached"] = False
    return saved
