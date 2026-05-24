"""
Shopify Billing API
- App インストール時に課金プランを作成
- /billing/confirm  →  Shopify の承認コールバックを受け取り charge を activate
"""
import os

import httpx
from fastapi import APIRouter, Query

router = APIRouter(prefix="/billing", tags=["billing"])

SHOPIFY_API_VERSION = "2024-04"
PLAN_PRICE = "29.00"  # USD / 月


async def create_recurring_charge(shop: str, access_token: str, return_url: str) -> str:
    """
    Shopify に月額課金レコードを作成し、承認URLを返す
    """
    url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/recurring_application_charges.json"
    payload = {
        "recurring_application_charge": {
            "name": "PostLift AI — Growth Plan",
            "price": PLAN_PRICE,
            "return_url": return_url,
            "test": os.getenv("SHOPIFY_BILLING_TEST", "true") == "true",
        }
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"X-Shopify-Access-Token": access_token},
        )
        resp.raise_for_status()

    charge = resp.json()["recurring_application_charge"]
    return charge["confirmation_url"]


@router.get("/confirm")
async def billing_confirm(
    charge_id: str = Query(...),
    shop: str = Query(...),
):
    """
    Shopify が承認後にリダイレクトするコールバック。
    charge を activate して DB に保存する。
    """
    # TODO: DB から access_token を取得して activate API を呼ぶ
    return {"status": "confirmed", "shop": shop, "charge_id": charge_id}
