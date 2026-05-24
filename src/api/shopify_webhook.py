"""
Shopify Webhook ハンドラー
POST /webhooks/orders/paid  →  注文完了後にアップセルオファーをトリガー
"""
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Header, HTTPException, Request

from src.ai.offer_engine import build_offer
from src.db.session import get_db

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


def _verify_hmac(body: bytes, hmac_header: str) -> bool:
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    import base64
    expected = base64.b64encode(digest.encode()).decode()
    return hmac.compare_digest(expected, hmac_header)


@router.post("/orders/paid")
async def orders_paid(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    body = await request.body()
    if not _verify_hmac(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC verification failed")

    order = json.loads(body)
    shop_domain = request.headers.get("x-shopify-shop-domain", "")

    async with get_db() as db:
        offer = await build_offer(
            db=db,
            shop_domain=shop_domain,
            order=order,
        )

    return {"status": "queued", "offer_id": offer["offer_id"]}
