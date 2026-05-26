"""
PostLift AI — FastAPI エントリポイント v3
- lifespan で DB プール・スケジューラーを管理
- レート制限 / エラーハンドラー / リクエスト ID ミドルウェア追加
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.ab_test import router as ab_test_router
from src.api.billing import router as billing_router
from src.api.dashboard import router as dashboard_router
from src.api.gdpr import router as gdpr_router
from src.api.merchants import router as merchants_router
from src.api.metrics import router as metrics_router
from src.api.offers import router as offers_router
from src.api.products import router as products_router
from src.api.proxy import router as proxy_router
from src.api.shopify_webhook import router as webhook_router
from src.db.session import close_pool, get_db, init_pool
from src.middleware.error_handler import GlobalErrorHandlerMiddleware, RequestIdMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.scheduler.daily_report import start_scheduler, stop_scheduler
from src.shopify.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    start_scheduler()
    yield
    stop_scheduler()
    await close_pool()


app = FastAPI(
    title="PostLift AI",
    description=(
        "Shopify 向け AI ポスト購入アップセル最適化 SaaS。\n\n"
        "注文完了直後に GPT-4o-mini が最適な商品をワンクリックで提案し、承諾率・追加売上を最大化します。\n\n"
        "**主な機能:** AI スコアリング / A/B テスト自動化 / 顧客 RFM スコアリング / KPI ダッシュボード / GDPR 対応\n\n"
        "[ダッシュボードを開く](/dashboard) | [トップページ](/)"
    ),
    version="0.4.0",
    lifespan=lifespan,
    docs_url="/docs",
)

# ミドルウェア（後から登録したものが外側になる）
app.add_middleware(GlobalErrorHandlerMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録
app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(gdpr_router)
app.include_router(billing_router)
app.include_router(metrics_router)
app.include_router(products_router)
app.include_router(merchants_router)
app.include_router(offers_router)
app.include_router(ab_test_router)
app.include_router(dashboard_router)
app.include_router(proxy_router)


@app.get("/health", tags=["システム"], summary="ヘルスチェック（DB 接続確認込み）")
async def health():
    """サーバーと DB の疎通状態を返します。`status: ok` なら正常稼働中です。"""
    try:
        async with get_db() as db:
            await db.fetchval("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "version": app.version,
        "db": db_status,
    }
