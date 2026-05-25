"""
Shopify Webhook ハンドラー
POST /webhooks/orders/paid      →  注文完了後にアップセルオファーをトリガー
POST /webhooks/upsell/respond   →  顧客の承諾・拒否を記録
"""
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.ai.offer_engine import build_offer
from src.db.session import get_db, get_db_dep

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


class UpsellResponse(BaseModel):
    offer_id: str
    accepted: bool


@router.post("/upsell/respond")
async def upsell_respond(
    payload: UpsellResponse,
    db=Depends(get_db_dep),
):
    """
    顧客がアップセルオファーに承諾・拒否したときの結果を記録する。
    - accepted=true  → 承諾（追加購入）
    - accepted=false → 拒否（スキップ）
    """
    row = await db.fetchrow(
        "SELECT id FROM upsell_offers WHERE id_str = $1",
        payload.offer_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="offer not found")

    await db.execute(
        """
        UPDATE upsell_offers
        SET accepted = $1, responded_at = $2
        WHERE id_str = $3
        """,
        payload.accepted,
        datetime.now(timezone.utc),
        payload.offer_id,
    )

    return {
        "offer_id": payload.offer_id,
        "accepted": payload.accepted,
        "status": "recorded",
    }
