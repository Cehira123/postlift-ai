"""
Shopify App Proxy
Shopify 管理画面から /apps/postlift/* へのリクエストを検証して、
KPI ダッシュボード HTML を返す。

設定（shopify.app.toml）:
  [app_proxy]
  url     = "https://your-app.replit.app"
  subpath = "postlift"
  prefix  = "apps"

Shopify は全クエリパラメータを `signature` で署名して送ってくる。
"""
import hashlib
import hmac
import os

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter(prefix="/proxy", tags=["proxy"])

SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "")


def _verify_proxy_signature(params: dict) -> bool:
    """
    App Proxy リクエストの HMAC 署名を検証する。
    https://shopify.dev/docs/apps/online-store/app-proxies#security
    """
    signature = params.pop("signature", "")
    if not signature:
        return False

    # パラメータをアルファベット順にソートして結合
    msg = "".join(f"{k}={','.join(v) if isinstance(v, list) else v}"
                  for k, v in sorted(params.items()))
    digest = hmac.new(SHOPIFY_API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.get("/dashboard")
async def proxy_dashboard(
    request: Request,
    shop: str = Query(...),
    signature: str = Query(...),
):
    """
    Shopify 管理画面内に埋め込まれるダッシュボード。
    署名を検証してから HTML を返す。
    """
    params = dict(request.query_params)
    is_valid = _verify_proxy_signature(dict(params))  # コピーで検証

    if not is_valid and os.getenv("SHOPIFY_PROXY_VERIFY", "true") == "true":
        return JSONResponse(status_code=403, content={"error": "invalid signature"})

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "shop_domain": shop},
    )


@router.get("/health")
async def proxy_health(
    shop: str = Query(...),
    signature: str = Query(""),
):
    """App Proxy の疎通確認用"""
    return {"status": "ok", "shop": shop}
