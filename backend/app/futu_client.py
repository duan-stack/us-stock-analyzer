from __future__ import annotations

import socket
import threading
import time
from typing import Any, Callable

from app.config import get_settings


def opend_reachable(host: str, port: int, timeout: float = 0.4) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _is_transport_error(message: str) -> bool:
    text = (message or "").lower()
    needles = ("无法连接", "connection", "timed out", "timeout", "broken pipe", "reset", "eof", "not connected")
    return any(item in text for item in needles)


class FutuError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class FutuQuoteClient:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._ctx: Any = None
        self._down_until = 0.0
        self._down_message = ""

    @property
    def host(self) -> str:
        return get_settings().futu_host

    @property
    def port(self) -> int:
        return get_settings().futu_port

    def _mark_down(self, message: str, cooldown: float = 3.0) -> None:
        self._down_until = time.time() + cooldown
        self._down_message = message

    def connect(self) -> None:
        self.close()
        if not opend_reachable(self.host, self.port):
            message = f"无法连接 FutuOpenD ({self.host}:{self.port})，请先启动并登录 OpenD"
            self._mark_down(message)
            raise FutuError(message)
        from futu import OpenQuoteContext

        self._ctx = OpenQuoteContext(host=self.host, port=self.port)
        self._down_until = 0.0
        self._down_message = ""

    def close(self) -> None:
        if self._ctx is not None:
            try:
                self._ctx.close()
            except Exception:
                pass
            self._ctx = None

    def _ensure(self) -> Any:
        if self._ctx is None:
            try:
                self.connect()
            except FutuError:
                raise
            except Exception as exc:
                raise FutuError(f"无法连接 FutuOpenD ({self.host}:{self.port}): {exc}") from exc
        return self._ctx

    def _unwrap(self, result: Any) -> Any:
        from futu import RET_OK

        if not isinstance(result, tuple) or not result:
            return result
        ret = result[0]
        if ret != RET_OK:
            err = result[1] if len(result) > 1 else "未知错误"
            raise FutuError(str(err))
        if len(result) == 2:
            return result[1]
        return result[1:]

    def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        now = time.time()
        if now < self._down_until:
            raise FutuError(self._down_message or f"无法连接 FutuOpenD ({self.host}:{self.port})，请先启动并登录 OpenD")
        if not opend_reachable(self.host, self.port):
            message = f"无法连接 FutuOpenD ({self.host}:{self.port})，请先启动并登录 OpenD"
            self._mark_down(message)
            raise FutuError(message)
        with self._lock:
            last_error: Exception | None = None
            for attempt in range(2):
                try:
                    ctx = self._ensure()
                    fn: Callable[..., Any] = getattr(ctx, method)
                    return self._unwrap(fn(*args, **kwargs))
                except FutuError as exc:
                    last_error = exc
                    if attempt == 0:
                        self.close()
                        time.sleep(0.15)
                        continue
                    if _is_transport_error(exc.message):
                        self._mark_down(exc.message)
                    raise
                except Exception as exc:
                    last_error = FutuError(f"OpenD 调用 {method} 失败: {exc}")
                    self.close()
                    if attempt == 0:
                        time.sleep(0.15)
                        continue
                    if _is_transport_error(str(last_error)):
                        self._mark_down(str(last_error))
                    raise last_error from exc
            raise last_error or FutuError("OpenD 调用失败")

    def ping(self) -> tuple[bool, dict[str, Any] | None, str | None]:
        now = time.time()
        if now < self._down_until:
            return False, None, self._down_message or f"无法连接 FutuOpenD ({self.host}:{self.port})，请先启动并登录 OpenD"
        if not opend_reachable(self.host, self.port):
            message = f"无法连接 FutuOpenD ({self.host}:{self.port})，请先启动并登录 OpenD"
            self._mark_down(message)
            return False, None, message
        try:
            state = self.call("get_global_state")
            if isinstance(state, dict):
                return True, state, None
            return True, {"raw": state}, None
        except FutuError as exc:
            self._mark_down(exc.message)
            return False, None, exc.message
        except Exception as exc:
            self._mark_down(str(exc))
            return False, None, str(exc)


_client: FutuQuoteClient | None = None
_client_lock = threading.Lock()


def get_quote_client() -> FutuQuoteClient:
    global _client
    with _client_lock:
        if _client is None:
            _client = FutuQuoteClient()
        return _client
