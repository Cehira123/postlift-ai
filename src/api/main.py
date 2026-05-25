"""
PostLift AI — FastAPI エントリポイント
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from src.api.billing import router as billing_router
from src.api.merchants import router as merchants_router
from src.api.metrics import router as metrics_router
from src.api.offers import router as offers_router
from src.api.products import router as products_router
from src.api.shopify_webhook import router as webhook_router
from src.db.session import close_pool, init_pool
from src.shopify.auth import router as auth_router

app = FastAPI(
    title="PostLift AI",
    description="Shopify向けAIポスト購入アップセル最適化SaaS",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_pool()


@app.on_event("shutdown")
async def shutdown():
    await close_pool()


app.include_router(auth_router)
app.include_router(webhook_router)
app.include_router(billing_router)
app.include_router(metrics_router)
app.include_router(products_router)
app.include_router(merchants_router)
app.include_router(offers_router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    return {"status": "ok"}
