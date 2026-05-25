"""
Shopify Admin API クライアント
- 商品・在庫・価格を取得して products テーブルに同期する
"""
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
    """
    Shopify Admin API から全商品を取得する（ページネーション対応）。
    返値: [{"id", "title", "variants": [{"price", "inventory_quantity", "cost"}]}]
    """
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
    """
    Shopify 商品リストを products テーブル用の行データに変換する。
    粗利率は cost_per_item（仕入れ値）から算出。
    """
    rows: list[dict] = []
    for product in products:
        for variant in product.get("variants", []):
            price = float(variant.get("price", 0))
            cost = float(variant.get("cost", 0) or 0)
            stock = int(variant.get("inventory_quantity", 0))

            if price <= 0:
                continue

            gross_margin = round((price - cost) / price * 100, 2) if cost > 0 else 0.0

            rows.append({
                "shop_domain": shop_domain,
                "product_id": str(product["id"]),
                "title": product.get("title", ""),
                "price": price,
                "gross_margin": gross_margin,
                "stock_qty": max(stock, 0),
            })

    return rows


async def sync_products_to_db(db, shop_domain: str, access_token: str) -> dict:
    """
    Shopify から商品を取得して DB を upsert する。
    Returns: {"synced": int, "skipped": int}
    """
    products = await fetch_products(shop_domain, access_token)
    rows = extract_product_rows(shop_domain, products)

    synced = 0
    for row in rows:
        await db.execute(
            """
            INSERT INTO products
                (shop_domain, product_id, title, price, gross_margin, stock_qty, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (shop_domain, product_id) DO UPDATE SET
                title        = EXCLUDED.title,
                price        = EXCLUDED.price,
                gross_margin = EXCLUDED.gross_margin,
                stock_qty    = EXCLUDED.stock_qty,
                updated_at   = NOW()
            """,
            row["shop_domain"],
            row["product_id"],
            row["title"],
            row["price"],
            row["gross_margin"],
            row["stock_qty"],
        )
        synced += 1

    return {"synced": synced, "total_fetched": len(products)}
