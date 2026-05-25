"""
グローバルエラーハンドラーミドルウェア
全ての未キャッチ例外を一貫した JSON フォーマットで返す。
リクエスト ID を付与してトレーサビリティを確保する。
"""
from __future__ import annotations

import traceback
import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """全リクエストに X-Request-ID ヘッダーを付与する"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4())[:8])
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class GlobalErrorHandlerMiddleware(BaseHTTPMiddleware):
    """未キャッチ例外を JSON エラーレスポンスに変換する"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", "unknown")
            tb = traceback.format_exc()
            print(f"[ERROR] request_id={request_id} path={request.url.path}\n{tb}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "detail": str(exc),
                    "request_id": request_id,
                },
            )
