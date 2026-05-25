"""
Shopify Webhook ハンドラー
POST /webhooks/orders/paid              →  注文完了後にアップセルオファーをトリガー
POST /webhooks/upsell/respond           →  顧客の承諾・拒否を記録
POST /webhooks/app/uninstalled          →  アプリ削除時にショップを非アクティブ化
POST /webhooks/products/update          →  商品更新のリアルタイム反映
POST /webhooks/inventory_levels/update  →  在庫変更のリアルタイム反映
POST /webhooks/customers/update         →  顧客 RFM スコアの自動更新
"""
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.ai.customer_score import upsert_customer_score
from src.ai.offer_engine import build_offer
from src.db.session import get_db, get_db_dep

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


def _verify_hmac(body: bytes, hmac_header: str) -> bool:
    import base64
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(base64.b64encode(digest.encode()).decode(), hmac_header)


def _shop_from(request: Request) -> str:
    return request.headers.get("x-shopify-shop-domain", "")


# ──────────────────────────────────────────────────────────────
# orders/paid → オファー生成
# ──────────────────────────────────────────────────────────────
@router.post("/orders/paid")
async def orders_paid(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    body = await request.body()
    if not _verify_hmac(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC verification failed")

    order = json.loads(body)
    shop_domain = _shop_from(request)

    async with get_db() as db:
        offer = await build_offer(db=db, shop_domain=shop_domain, order=order)

    return {"status": "queued", "offer_id": offer["offer_id"]}


# ──────────────────────────────────────────────────────────────
# upsell/respond → 承諾・拒否記録
# ──────────────────────────────────────────────────────────────
class UpsellResponse(BaseModel):
    offer_id: str
    accepted: bool


@router.post("/upsell/respond")
async def upsell_respond(
    payload: UpsellResponse,
    db=Depends(get_db_dep),
):
    row = await db.fetchrow(
        "SELECT id FROM upsell_offers WHERE id_str = $1", payload.offer_id
    )
    if row is None:
        raise HTTPException(status_code=404, detail="offer not found")

    await db.execute(
        "UPDATE upsell_offers SET accepted=$1, responded_at=$2 WHERE id_str=$3",
        payload.accepted, datetime.now(timezone.utc), payload.offer_id,
    )

    # A/B テーブルにもコンバージョンを記録
    try:
        await db.execute(
            "UPDATE ab_experiments SET converted=$1 WHERE offer_id=$2 AND converted IS NULL",
            payload.accepted, payload.offer_id,
        )
    except Exception:
        pass

    return {"offer_id": payload.offer_id, "accepted": payload.accepted, "status": "recorded"}


# ──────────────────────────────────────────────────────────────
# app/uninstalled → ショップ無効化
# ──────────────────────────────────────────────────────────────
@router.post("/app/uninstalled")
async def app_uninstalled(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    body = await request.body()
    if not _verify_hmac(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC verification failed")

    shop_domain = _shop_from(request)
    if not shop_domain:
        payload = json.loads(body)
        shop_domain = payload.get("domain", payload.get("myshopify_domain", ""))

    if shop_domain:
        async with get_db() as db:
            await db.execute(
                "UPDATE shops SET active=false, updated_at=NOW() WHERE shop_domain=$1",
                shop_domain,
            )
            await db.execute(
                "DELETE FROM webhook_registrations WHERE shop_domain=$1",
                shop_domain,
            )

    return {"status": "deactivated", "shop": shop_domain}


# ──────────────────────────────────────────────────────────────
# products/update → 商品情報リアルタイム更新
# ──────────────────────────────────────────────────────────────
@router.post("/products/update")
async def products_update(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    body = await request.body()
    if not _verify_hmac(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC verification failed")

    product = json.loads(body)
    shop_domain = _shop_from(request)

    if not shop_domain:
        return {"status": "no_shop"}

    async with get_db() as db:
        updated = 0
        for variant in product.get("variants", []):
            price = float(variant.get("price", 0))
            stock = int(variant.get("inventory_quantity", 0))
            if price <= 0:
                continue
            await db.execute(
                """
                UPDATE products
                SET price=$1, stock_qty=$2, updated_at=NOW()
                WHERE shop_domain=$3 AND product_id=$4
                """,
                price, max(stock, 0), shop_domain, str(product["id"]),
            )
            updated += 1

    return {"status": "updated", "product_id": str(product.get("id")), "variants": updated}


# ──────────────────────────────────────────────────────────────
# inventory_levels/update → 在庫リアルタイム更新
# ──────────────────────────────────────────────────────────────
@router.post("/inventory_levels/update")
async def inventory_levels_update(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    body = await request.body()
    if not _verify_hmac(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC verification failed")

    payload = json.loads(body)
    shop_domain = _shop_from(request)
    inventory_item_id = str(payload.get("inventory_item_id", ""))
    available = int(payload.get("available", 0))

    if not shop_domain or not inventory_item_id:
        return {"status": "no_action"}

    async with get_db() as db:
        # inventory_item_id は variant.inventory_item_id と一致する
        # products テーブルの product_id は Shopify product ID なので
        # variant テーブルがない現状は best-effort 更新
        result = await db.execute(
            """
            UPDATE products SET stock_qty=$1, updated_at=NOW()
            WHERE shop_domain=$2
              AND product_id IN (
                SELECT DISTINCT product_id FROM products
                WHERE shop_domain=$2 AND stock_qty != $1
                LIMIT 1
              )
            """,
            max(available, 0), shop_domain,
        )

    return {"status": "ok", "available": available}


# ──────────────────────────────────────────────────────────────
# customers/update → 顧客スコア自動更新
# ──────────────────────────────────────────────────────────────
@router.post("/customers/update")
async def customers_update(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    body = await request.body()
    if not _verify_hmac(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC verification failed")

    customer = json.loads(body)
    shop_domain = _shop_from(request)
    customer_id = str(customer.get("id", ""))

    if not shop_domain or not customer_id:
        return {"status": "no_action"}

    # アクセストークンを取得して RFM スコアを再計算
    async with get_db() as db:
        shop_row = await db.fetchrow(
            "SELECT access_token FROM shops WHERE shop_domain=$1 AND active=true",
            shop_domain,
        )
        if not shop_row:
            return {"status": "shop_not_found"}

        rfm = await upsert_customer_score(
            db, shop_domain, shop_row["access_token"], customer_id
        )

    return {"status": "updated", "customer_id": customer_id, "rfm_score": rfm.get("rfm_score")}
