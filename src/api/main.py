"""PostLift AI FastAPI application."""
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.ab_test import router as ab_test_router
from src.api.billing import router as billing_router
from src.api.dashboard import router as dashboard_router
from src.api.demo import router as demo_router
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


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw:
        return ["http://localhost:3000", "http://localhost:5000", "http://127.0.0.1:5000"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pool()
    if os.getenv("RUN_SCHEDULER", "true").lower() == "true":
        start_scheduler()
    yield
    stop_scheduler()
    await close_pool()


app = FastAPI(
    title="PostLift AI",
    description=(
        "AI-powered post-purchase upsell optimization for Shopify. "
        "Scores products by margin, inventory, acceptance history, and customer fit."
    ),
    version="0.4.0",
    lifespan=lifespan,
    docs_url="/docs",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GlobalErrorHandlerMiddleware)

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
app.include_router(demo_router)


@app.get("/health", tags=["system"], summary="Health check")
async def health():
    """Return application and database health."""
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
