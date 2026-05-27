"""Shopify Admin API client for product synchronization."""
from __future__ import annotations

import os
from typing import Any

import httpx

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")


async def _get(shop: str, access_token: str, path: str, params: dict | None = None) -> Any:
    url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            url,
            params=params or {},
            headers={"X-Shopify-Access-Token": access_token},
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_products(shop: str, access_token: str, limit: int = 250) -> list[dict]:
    """Fetch products with variants from Shopify Admin API."""
    all_products: list[dict] = []
    page_info: str | None = None

    while True:
        params: dict = {"limit": limit, "fields": "id,title,variants"}
        if page_info:
            params["page_info"] = page_info

        data = await _get(shop, access_token, "products.json", params)
        products = data.get("products", [])
        all_products.extend(products)

        if len(products) < limit:
            break

        link = data.get("link", "")
        if 'rel="next"' not in link:
            break
        for part in link.split(","):
            if 'rel="next"' in part:
                page_info = part.split("page_info=")[1].split(">")[0]
                break

    return all_products


def extract_product_rows(shop_domain: str, products: list[dict]) -> list[dict]:
    """Convert Shopify products into offerable variant rows.

    Shopify post-purchase `add_variant` requires a variant ID, so the local
    `product_id` column intentionally stores the Shopify variant ID.
    """
    rows: list[dict] = []
    for product in products:
        product_title = product.get("title", "")
        for variant in product.get("variants", []):
            variant_id = variant.get("id")
            price = float(variant.get("price", 0))
            cost = float(variant.get("cost", 0) or 0)
            stock = int(variant.get("inventory_quantity", 0))

            if price <= 0 or not variant_id:
                continue

            gross_margin = round((price - cost) / price * 100, 2) if cost > 0 else 0.0
            variant_title = variant.get("title")
            title = product_title
            if variant_title and variant_title != "Default Title":
                title = f"{product_title} - {variant_title}"

            rows.append(
                {
                    "shop_domain": shop_domain,
                    "product_id": str(variant_id),
                    "inventory_item_id": str(variant.get("inventory_item_id", "")),
                    "title": title,
                    "price": price,
                    "gross_margin": gross_margin,
                    "stock_qty": max(stock, 0),
                }
            )

    return rows


async def sync_products_to_db(db, shop_domain: str, access_token: str) -> dict:
    """Fetch Shopify products and upsert offerable variants into the database."""
    products = await fetch_products(shop_domain, access_token)
    rows = extract_product_rows(shop_domain, products)

    synced = 0
    for row in rows:
        await db.execute(
            """
            INSERT INTO products
                (shop_domain, product_id, inventory_item_id, title, price, gross_margin, stock_qty, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            ON CONFLICT (shop_domain, product_id) DO UPDATE SET
                inventory_item_id = EXCLUDED.inventory_item_id,
                title             = EXCLUDED.title,
                price             = EXCLUDED.price,
                gross_margin      = EXCLUDED.gross_margin,
                stock_qty         = EXCLUDED.stock_qty,
                updated_at        = NOW()
            """,
            row["shop_domain"],
            row["product_id"],
            row["inventory_item_id"],
            row["title"],
            row["price"],
            row["gross_margin"],
            row["stock_qty"],
        )
        synced += 1

    return {"synced": synced, "total_fetched": len(products)}
