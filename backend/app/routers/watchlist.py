from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.codes import is_us_code, normalize_code
from app.db import add_watchlist, list_watchlist, remove_watchlist
from app.futu_client import FutuError
from app.services.snapshot import get_snapshots

router = APIRouter(tags=["watchlist"])


class WatchlistIn(BaseModel):
    code: str = Field(..., min_length=1)
    name: str = ""


@router.get("/api/watchlist")
def get_watchlist() -> dict:
    return {"items": list_watchlist()}


@router.post("/api/watchlist")
def post_watchlist(body: WatchlistIn) -> dict:
    try:
        code = normalize_code(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not is_us_code(code):
        raise HTTPException(status_code=400, detail="本系统仅支持美股")
    name = body.name.strip()
    if not name:
        try:
            snaps = get_snapshots([code])
            if snaps and snaps[0].get("name"):
                name = str(snaps[0]["name"])
        except FutuError:
            name = code
    item = add_watchlist(code, name or code)
    return {"item": item}


@router.delete("/api/watchlist/{code}")
def delete_watchlist(code: str) -> dict:
    try:
        normalized = normalize_code(code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    removed = remove_watchlist(normalized)
    if not removed:
        raise HTTPException(status_code=404, detail=f"自选中不存在 {normalized}")
    return {"ok": True, "code": normalized}
