"""
Shopify OAuth 2.0 認証フロー
/auth/install   →  インストール開始（Shopify の認証画面へリダイレクト）
/auth/callback  →  アクセストークンを取得 → DB 保存 → Webhook 自動登録 → 初回商品同期
"""
import hashlib
import hmac
import os
import urllib.parse

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import RedirectResponse

from src.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

SHOPIFY_API_KEY    = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
APP_URL            = os.getenv("APP_URL", "https://your-app.com")
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04")

SCOPES = (
    "read_orders,"
    "read_products,"
    "read_inventory,"
    "write_draft_orders,"
    "read_customers"
)

# インストール後に自動登録する Webhook トピック
WEBHOOK_TOPICS = [
    "orders/paid",
    "products/update",
    "inventory_levels/update",
    "customers/update",
    "app/uninstalled",
    "customers/redact",
    "customers/data_request",
    "shop/redact",
]


@router.get("/install")
def install(shop: str = Query(...)):
    nonce = os.urandom(16).hex()
    params = {
        "client_id": SHOPIFY_API_KEY,
        "scope": SCOPES,
        "redirect_uri": f"{APP_URL}/auth/callback",
        "state": nonce,
    }
    url = f"https://{shop}/admin/oauth/authorize?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url)


@router.get("/callback")
async def callback(
    request: Request,
    code: str = Query(...),
    shop: str = Query(...),
    state: str = Query(...),
    hmac_param: str = Query(..., alias="hmac"),
):
    # HMAC 検証
    query_params = dict(request.query_params)
    query_params.pop("hmac", None)
    sorted_params = "&".join(f"{k}={v}" for k, v in sorted(query_params.items()))
    digest = hmac.new(
        SHOPIFY_API_SECRET.encode(), sorted_params.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(digest, hmac_param):
        return {"error": "HMAC mismatch"}

    # アクセストークン取得
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": SHOPIFY_API_KEY,
                "client_secret": SHOPIFY_API_SECRET,
                "code": code,
            },
        )
        resp.raise_for_status()
        access_token = resp.json()["access_token"]

    # DB に shops + merchants を upsert
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO shops (shop_domain, access_token, active)
            VALUES ($1, $2, true)
            ON CONFLICT (shop_domain) DO UPDATE SET access_token=$2, active=true
            """,
            shop, access_token,
        )
        await db.execute(
            "INSERT INTO merchants (shop_domain) VALUES ($1) ON CONFLICT DO NOTHING",
            shop,
        )

    # Webhook を非同期で登録（失敗してもインストールは続行）
    try:
        await _register_webhooks(shop, access_token)
    except Exception as e:
        print(f"[auth] webhook registration failed for {shop}: {e}")

    # 初回商品同期（失敗してもインストールは続行）
    try:
        from src.shopify.admin_api import sync_products_to_db
        async with get_db() as db:
            result = await sync_products_to_db(db, shop, access_token)
        print(f"[auth] initial product sync for {shop}: {result}")
    except Exception as e:
        print(f"[auth] initial product sync failed for {shop}: {e}")

    return RedirectResponse(f"https://{shop}/admin/apps")


async def _register_webhooks(shop: str, access_token: str) -> None:
    """
    全 Webhook トピックを Shopify に登録して DB に記録する。
    既存の Webhook は重複登録しない（ON CONFLICT で更新のみ）。
    """
    registered = []
    async with httpx.AsyncClient(timeout=20) as client:
        for topic in WEBHOOK_TOPICS:
            address = _webhook_address(topic)
            try:
                resp = await client.post(
                    f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/webhooks.json",
                    json={"webhook": {"topic": topic, "address": address, "format": "json"}},
                    headers={"X-Shopify-Access-Token": access_token},
                )
                if resp.status_code in (201, 422):  # 422 = already exists
                    data = resp.json()
                    shopify_id = (
                        data.get("webhook", {}).get("id")
                        if resp.status_code == 201 else None
                    )
                    registered.append((topic, shopify_id, address))
            except Exception as e:
                print(f"[auth] failed to register webhook {topic}: {e}")

    async with get_db() as db:
        for topic, shopify_id, address in registered:
            await db.execute(
                """
                INSERT INTO webhook_registrations (shop_domain, topic, shopify_id, address)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (shop_domain, topic) DO UPDATE
                SET shopify_id=$3, address=$4, created_at=NOW()
                """,
                shop, topic, shopify_id, address,
            )


def _webhook_address(topic: str) -> str:
    """Webhook トピックを API エンドポイント URL に変換する"""
    path_map = {
        "orders/paid":              "/webhooks/orders/paid",
        "products/update":          "/webhooks/products/update",
        "inventory_levels/update":  "/webhooks/inventory_levels/update",
        "customers/update":         "/webhooks/customers/update",
        "app/uninstalled":          "/webhooks/app/uninstalled",
        "customers/redact":         "/webhooks/customers/redact",
        "customers/data_request":   "/webhooks/customers/data_request",
        "shop/redact":              "/webhooks/shop/redact",
    }
    return APP_URL + path_map.get(topic, f"/webhooks/{topic.replace('/', '/')}")
