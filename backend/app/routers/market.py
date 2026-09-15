from fastapi import APIRouter

from app.db import list_watchlist
from app.futu_client import FutuError, get_quote_client
from app.routers.health import market_state_label
from app.services.serialize import df_records
from app.services.snapshot import get_snapshots, shape_hot, shape_rank
from app.services.us_session import us_equity_session

router = APIRouter(tags=["market"])


def _empty_block(error: str | None) -> dict:
    return {"available": False, "error": error, "items": []}


def _empty_board(error: str | None) -> dict:
    return {
        "top_gainers": _empty_block(error),
        "top_losers": _empty_block(error),
        "hot_list": _empty_block(error),
    }


def _optional_rank(market: object, sort_dir: object | None) -> dict:
    try:
        kwargs = {"market": market, "count": 10}
        if sort_dir is not None:
            kwargs["sort_dir"] = sort_dir
        data = get_quote_client().call("get_top_movers_rank", **kwargs)
        df = data[1] if isinstance(data, tuple) and len(data) >= 2 else data
        return {"available": True, "items": [shape_rank(row) for row in df_records(df)]}
    except FutuError as exc:
        return {"available": False, "error": exc.message, "items": []}
    except Exception as exc:
        return {"available": False, "error": str(exc), "items": []}


def _optional_hot(market: object) -> dict:
    try:
        data = get_quote_client().call("get_hot_list", market=market, count=10)
        df = data[1] if isinstance(data, tuple) and len(data) >= 2 else data
        return {"available": True, "items": [shape_hot(row) for row in df_records(df)]}
    except FutuError as exc:
        return {"available": False, "error": exc.message, "items": []}
    except Exception as exc:
        return {"available": False, "error": str(exc), "items": []}


def _board_for(market_name: str, desc: object | None, asc: object | None) -> dict:
    try:
        from futu import Market

        market = getattr(Market, market_name)
    except Exception as exc:
        return _empty_board(str(exc))
    return {
        "top_gainers": _optional_rank(market, desc),
        "top_losers": _optional_rank(market, asc),
        "hot_list": _optional_hot(market),
    }


@router.get("/api/market/overview")
def overview() -> dict:
    client = get_quote_client()
    ok, state, error = client.ping()
    watch_items = list_watchlist()
    snapshots: list[dict] = []
    snap_error = None
    if ok and watch_items:
        try:
            snapshots = get_snapshots([item["code"] for item in watch_items])
        except FutuError as exc:
            snap_error = exc.message
            snapshots = [{"code": item["code"], "name": item.get("name")} for item in watch_items]
    else:
        snapshots = [{"code": item["code"], "name": item.get("name")} for item in watch_items]
        if not ok:
            snap_error = error

    us_board = _empty_board(error)
    if ok:
        try:
            from futu import RankSortDir

            desc = getattr(RankSortDir, "DESCEND", None) or getattr(RankSortDir, "DESCENDING", None)
            asc = getattr(RankSortDir, "ASCEND", None) or getattr(RankSortDir, "ASCENDING", None)
        except Exception:
            desc = None
            asc = None
        us_board = _board_for("US", desc, asc)

    market_us = state.get("market_us") if isinstance(state, dict) else None
    session = us_equity_session()
    return {
        "opend_connected": ok,
        "error": None if ok else (error or "请启动 FutuOpenD"),
        "global_state": state,
        "market_us": market_us,
        "market_us_label": market_state_label(str(market_us) if market_us is not None else None),
        "us_session": session,
        "watchlist": snapshots,
        "watchlist_error": snap_error,
        "us": us_board,
        "top_gainers": us_board["top_gainers"],
        "top_losers": us_board["top_losers"],
        "hot_list": us_board["hot_list"],
    }
