"""
PostLift AI — FastAPI エントリポイント v2
- lifespan イベントで DB プール & スケジューラーを管理
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from src.api.ab_test import router as ab_test_router
from src.api.billing import router as billing_router
from src.api.dashboard import router as dashboard_router
from src.api.merchants import router as merchants_router
from src.api.metrics import router as metrics_router
from src.api.offers import router as offers_router
from src.api.products import router as products_router
from src.api.shopify_webhook import router as webhook_router
from src.db.session import close_pool, init_pool
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
    description="Shopify向けAIポスト購入アップセル最適化SaaS",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(billing_router)
app.include_router(metrics_router)
app.include_router(products_router)
app.include_router(merchants_router)
app.include_router(offers_router)
app.include_router(ab_test_router)
app.include_router(dashboard_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok", "version": app.version}
