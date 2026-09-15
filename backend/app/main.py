from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import PROJECT_ROOT, get_settings
from app.db import init_db
from app.futu_client import FutuError, get_quote_client
from app.routers import health, market, stocks, watchlist

DIST_DIR = PROJECT_ROOT / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield
    get_quote_client().close()


app = FastAPI(title="美股投研", lifespan=lifespan)
cors_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
    *[item.strip() for item in get_settings().cors_origins.split(",") if item.strip()],
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(market.router)
app.include_router(stocks.router)
app.include_router(watchlist.router)


@app.exception_handler(FutuError)
async def futu_error_handler(_: Request, exc: FutuError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": exc.message})


@app.get("/api")
def api_root() -> dict:
    return {"name": "美股投研", "docs": "/docs"}


if DIST_DIR.is_dir():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/")
    def spa_index():
        return FileResponse(DIST_DIR / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        reserved = {"api", "docs", "redoc", "openapi.json"}
        first = full_path.split("/", 1)[0]
        if first in reserved:
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        candidate = DIST_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(DIST_DIR / "index.html")
