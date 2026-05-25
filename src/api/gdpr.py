"""
Shopify GDPR Mandatory Webhooks
Shopify App Store 掲載に必須の 3 エンドポイント。
POST /webhooks/customers/redact        → 顧客データ削除
POST /webhooks/customers/data_request  → 顧客データ開示リクエスト
POST /webhooks/shop/redact             → ショップデータ削除
"""
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Header, HTTPException, Request

from src.db.session import get_db

router = APIRouter(prefix="/webhooks", tags=["gdpr"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


def _verify(body: bytes, hmac_header: str) -> bool:
    import base64
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
    """
    顧客から自身のデータ削除を Shopify が要求するときに呼ばれる。
    該当顧客に紐づくスコア・オファー履歴を匿名化する。
    """
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
        # 顧客スコアを削除
        await db.execute(
            "DELETE FROM customer_scores WHERE shop_domain=$1 AND customer_id=$2",
            shop_domain, customer_id,
        )
        # オファー履歴の customer_id を匿名化
        await db.execute(
            "UPDATE upsell_offers SET customer_id=NULL WHERE shop_domain=$1 AND customer_id=$2",
            shop_domain, customer_id,
        )

    return {"status": "deleted", "customer_id": customer_id}


@router.post("/customers/data_request")
async def customers_data_request(
    request: Request,
    x_shopify_hmac_sha256: str = Header(...),
):
    """
    顧客が自身のデータ開示を Shopify に要求したときに呼ばれる。
    保持しているデータのサマリーを返す（実際の通知は店舗オーナーへ）。
    """
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
                shop_domain, customer_id,
            )
            offer_count = await db.fetchval(
                "SELECT COUNT(*) FROM upsell_offers WHERE shop_domain=$1 AND customer_id=$2",
                shop_domain, customer_id,
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
    """
    ショップがアプリをアンインストールして 48 時間後に Shopify が呼ぶ。
    該当ショップの全データを完全削除する。
    """
    body = await request.body()
    if not _verify(body, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="HMAC mismatch")

    payload = json.loads(body)
    shop_domain = payload.get("shop_domain", "")

    if not shop_domain:
        return {"status": "no_action"}

    async with get_db() as db:
        # 依存関係の逆順に削除
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
