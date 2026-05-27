"""
Shopify privacy webhooks for self-hosted deployments.

POST /webhooks/customers/redact
POST /webhooks/customers/data_request
POST /webhooks/shop/redact
"""
import base64
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Header, HTTPException, Request

from src.db.session import get_db

router = APIRouter(prefix="/webhooks", tags=["gdpr"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


def _verify(body: bytes, hmac_header: str) -> bool:
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(
        base64.b64encode(digest.encode()).decode(), hmac_header
    )


@router.post("/customers/redact")
async def customers_redact(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    """Delete stored customer score data and anonymize offer history."""
    body = await request.body()
    if not _verify(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC mismatch")

    payload = json.loads(body)
    shop_domain = payload.get("shop_domain", "")
    customer = payload.get("customer", {})
    customer_id = str(customer.get("id", ""))

    if not shop_domain or not customer_id:
        return {"status": "no_action"}

    async with get_db() as db:
        await db.execute(
            "DELETE FROM customer_scores WHERE shop_domain=$1 AND customer_id=$2",
            shop_domain,
            customer_id,
        )
        await db.execute(
            "UPDATE upsell_offers SET customer_id=NULL WHERE shop_domain=$1 AND customer_id=$2",
            shop_domain,
            customer_id,
        )

    return {"status": "deleted", "customer_id": customer_id}


@router.post("/customers/data_request")
async def customers_data_request(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    """Return a summary of customer-linked data held by this deployment."""
    body = await request.body()
    if not _verify(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC mismatch")

    payload = json.loads(body)
    shop_domain = payload.get("shop_domain", "")
    customer_id = str(payload.get("customer", {}).get("id", ""))

    data_held = []

    if shop_domain and customer_id:
        async with get_db() as db:
            score_row = await db.fetchrow(
                "SELECT * FROM customer_scores WHERE shop_domain=$1 AND customer_id=$2",
                shop_domain,
                customer_id,
            )
            offer_count = await db.fetchval(
                "SELECT COUNT(*) FROM upsell_offers WHERE shop_domain=$1 AND customer_id=$2",
                shop_domain,
                customer_id,
            )
        if score_row:
            data_held.append("customer_rfm_score")
        if offer_count:
            data_held.append(f"upsell_offer_history ({offer_count} records)")

    return {"status": "acknowledged", "data_held": data_held}


@router.post("/shop/redact")
async def shop_redact(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    """Delete all stored data for a shop after uninstall or erasure request."""
    body = await request.body()
    if not _verify(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC mismatch")

    payload = json.loads(body)
    shop_domain = payload.get("shop_domain", "")

    if not shop_domain:
        return {"status": "no_action"}

    async with get_db() as db:
        await db.execute("DELETE FROM ab_experiments   WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM kpi_snapshots    WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM upsell_offers    WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM customer_scores  WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM products         WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM billing          WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM webhook_registrations WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM merchants        WHERE shop_domain=$1", shop_domain)
        await db.execute("DELETE FROM shops            WHERE shop_domain=$1", shop_domain)

    return {"status": "purged", "shop": shop_domain}
