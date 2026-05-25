"""
レート制限ミドルウェア — スライディングウィンドウ方式（インメモリ）
デフォルト: 60 リクエスト / 60 秒 / IP
Webhook エンドポイントは除外する。
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# レート制限設定
RATE_LIMIT_REQUESTS = 120   # 最大リクエスト数
RATE_LIMIT_WINDOW   = 60    # ウィンドウ秒数
RATE_LIMIT_EXEMPT_PREFIXES = ("/webhooks/", "/health", "/docs", "/openapi")

# IP ごとのタイムスタンプキュー
_windows: dict[str, deque[float]] = defaultdict(deque)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if any(path.startswith(p) for p in RATE_LIMIT_EXEMPT_PREFIXES):
            return await call_next(request)

        ip = _get_client_ip(request)
        now = time.monotonic()
        window = _windows[ip]

        # 古いエントリを削除
        while window and now - window[0] > RATE_LIMIT_WINDOW:
            window.popleft()

        if len(window) >= RATE_LIMIT_REQUESTS:
            retry_after = int(RATE_LIMIT_WINDOW - (now - window[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"error": "rate_limit_exceeded", "retry_after": retry_after},
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"]     = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Remaining"] = str(RATE_LIMIT_REQUESTS - len(window))
        return response
