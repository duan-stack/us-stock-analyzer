from __future__ import annotations

import secrets
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings

COOKIE_NAME = "us_access"


def access_configured() -> bool:
    return bool(get_settings().access_token.strip())


def token_ok(value: str | None) -> bool:
    expected = get_settings().access_token.strip()
    if not expected:
        return True
    if not value:
        return False
    return secrets.compare_digest(value.strip(), expected)


class AccessGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        if not access_configured():
            return await call_next(request)

        path = request.url.path or "/"
        if path in {"/api/access/login", "/api/access/status", "/api/health"}:
            return await call_next(request)
        if path.startswith("/assets/") or path.endswith((".js", ".css", ".ico", ".png", ".svg", ".woff2")):
            return await call_next(request)

        cookie = request.cookies.get(COOKIE_NAME)
        header = request.headers.get("X-Access-Token")
        if token_ok(cookie) or token_ok(header):
            return await call_next(request)

        # SPA shell can load; API is blocked.
        if path.startswith("/api"):
            return JSONResponse({"detail": "需要访问口令"}, status_code=401)
        return await call_next(request)


def set_access_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        max_age=30 * 24 * 3600,
        path="/",
    )


def clear_access_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
