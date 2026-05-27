"""
Optional Shopify Billing API helpers.

Self-hosted buyers can leave these routes unused. They are provided for buyers
who later choose to turn their own deployment into a paid Shopify app.
"""
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.session import get_db_dep

router = APIRouter(prefix="/billing", tags=["billing"])

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")
APP_URL = os.getenv("APP_URL", "https://your-app.com")

PLANS = {
    "starter": {"name": "PostLift AI - Starter", "price": "29.00"},
    "growth": {"name": "PostLift AI - Growth", "price": "79.00"},
    "scale": {"name": "PostLift AI - Scale", "price": "199.00"},
}


async def _shopify_post(shop: str, access_token: str, path: str, payload: dict) -> dict:
    url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            url,
            json=payload,
            headers={"X-Shopify-Access-Token": access_token},
        )
        resp.raise_for_status()
        return resp.json()


async def create_recurring_charge(
    shop: str,
    access_token: str,
    plan: str = "starter",
) -> str:
    """Create a Shopify recurring charge and return the approval URL."""
    if plan not in PLANS:
        raise ValueError(f"unknown plan: {plan}")

    plan_info = PLANS[plan]
    return_url = f"{APP_URL}/billing/confirm?plan={plan}"
    payload = {
        "recurring_application_charge": {
            "name": plan_info["name"],
            "price": plan_info["price"],
            "return_url": return_url,
            "test": os.getenv("SHOPIFY_BILLING_TEST", "true") == "true",
            "trial_days": 14,
        }
    }
    data = await _shopify_post(
        shop, access_token, "recurring_application_charges.json", payload
    )
    charge = data["recurring_application_charge"]
    return charge["confirmation_url"]


@router.get("/start")
async def billing_start(
    shop_domain: str = Query(...),
    plan: str = Query("starter", pattern="^(starter|growth|scale)$"),
    db=Depends(get_db_dep),
):
    """Start the optional Shopify billing approval flow."""
    shop = await db.fetchrow(
        "SELECT access_token FROM shops WHERE shop_domain = $1 AND active = true",
        shop_domain,
    )
    if not shop:
        raise HTTPException(status_code=404, detail="shop not found")

    confirmation_url = await create_recurring_charge(
        shop_domain, shop["access_token"], plan
    )
    return {"confirmation_url": confirmation_url, "plan": plan}


@router.get("/confirm")
async def billing_confirm(
    charge_id: str = Query(...),
    shop: str = Query(...),
    plan: str = Query("starter"),
    db=Depends(get_db_dep),
):
    """Activate the optional Shopify charge after the buyer approves it."""
    shop_row = await db.fetchrow(
        "SELECT access_token FROM shops WHERE shop_domain = $1 AND active = true",
        shop,
    )
    if not shop_row:
        raise HTTPException(status_code=404, detail="shop not found")

    access_token = shop_row["access_token"]

    try:
        data = await _shopify_post(
            shop,
            access_token,
            f"recurring_application_charges/{charge_id}/activate.json",
            {},
        )
        charge = data["recurring_application_charge"]
        status = charge.get("status", "active")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Shopify activate failed: {e.response.text}",
        )

    await db.execute(
        """
        INSERT INTO billing (shop_domain, charge_id, status, plan, price_usd, activated_at)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (charge_id) DO UPDATE SET status = $3, activated_at = $6
        """,
        shop,
        str(charge_id),
        status,
        plan,
        float(PLANS.get(plan, PLANS["starter"])["price"]),
        datetime.now(timezone.utc),
    )

    await db.execute(
        "UPDATE shops SET plan = $1 WHERE shop_domain = $2",
        plan,
        shop,
    )
    await db.execute(
        """
        INSERT INTO merchants (shop_domain, plan)
        VALUES ($1, $2)
        ON CONFLICT (shop_domain) DO UPDATE SET plan = $2, updated_at = NOW()
        """,
        shop,
        plan,
    )

    return {"status": status, "shop": shop, "charge_id": charge_id, "plan": plan}
