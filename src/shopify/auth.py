"""
Shopify OAuth 2.0 認証フロー
/auth/install   →  インストール開始 (Shopify の認証画面へリダイレクト)
/auth/callback  →  アクセストークンを取得して DB に保存
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

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY", "")
SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")
APP_URL = os.getenv("APP_URL", "https://your-app.com")
SCOPES = "read_orders,read_products,write_checkouts"


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
    digest = hmac.new(SHOPIFY_API_SECRET.encode(), sorted_params.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, hmac_param):
        return {"error": "HMAC mismatch"}

    # アクセストークン取得
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={"client_id": SHOPIFY_API_KEY, "client_secret": SHOPIFY_API_SECRET, "code": code},
        )
        resp.raise_for_status()
        access_token = resp.json()["access_token"]

    # DB に保存
    async with get_db() as db:
        await db.execute(
            """
            INSERT INTO shops (shop_domain, access_token, active)
            VALUES ($1, $2, true)
            ON CONFLICT (shop_domain) DO UPDATE SET access_token = $2, active = true
            """,
            shop, access_token,
        )

    return RedirectResponse(f"https://{shop}/admin/apps")
