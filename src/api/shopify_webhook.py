"""Shopify webhook handlers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel

from src.ai.customer_score import upsert_customer_score
from src.ai.offer_engine import build_offer
from src.db.session import get_db, get_db_dep

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


def _verify_hmac(body: bytes, hmac_header: str) -> bool:
    """Verify Shopify's base64-encoded HMAC-SHA256 webhook signature."""
    if not SHOPIFY_WEBHOOK_SECRET or not hmac_header:
        return False
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"), body, hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, hmac_header)


def _shop_from(request: Request) -> str:
    return request.headers.get("x-shopify-shop-domain", "")


@router.post("/orders/paid")
async def orders_paid(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    body = await request.body()
    if not _verify_hmac(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC verification failed")

    try:
        order = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON payload")

    shop_domain = _shop_from(request)
    if not shop_domain:
        raise HTTPException(status_code=400, detail="missing shop domain")

    async with get_db() as db:
        offer = await build_offer(db=db, shop_domain=shop_domain, order=order)

    return {"status": "queued", "offer_id": offer["offer_id"]}


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
        payload.accepted,
        datetime.now(timezone.utc),
        payload.offer_id,
    )

    try:
        await db.execute(
            "UPDATE ab_experiments SET converted=$1 WHERE offer_id=$2 AND converted IS NULL",
            payload.accepted,
            payload.offer_id,
        )
    except Exception:
        pass

    return {"offer_id": payload.offer_id, "accepted": payload.accepted, "status": "recorded"}


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
            variant_id = variant.get("id")
            if price <= 0 or not variant_id:
                continue
            await db.execute(
                """
                UPDATE products
                SET price=$1, stock_qty=$2, inventory_item_id=$3, updated_at=NOW()
                WHERE shop_domain=$4 AND product_id=$5
                """,
                price,
                max(stock, 0),
                str(variant.get("inventory_item_id", "")),
                shop_domain,
                str(variant_id),
            )
            updated += 1

    return {"status": "updated", "product_id": str(product.get("id")), "variants": updated}


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
        await db.execute(
            """
            UPDATE products SET stock_qty=$1, updated_at=NOW()
            WHERE shop_domain=$2 AND inventory_item_id=$3
            """,
            max(available, 0),
            shop_domain,
            inventory_item_id,
        )

    return {"status": "ok", "available": available}


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
