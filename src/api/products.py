"""
商品同期 API
POST /products/sync        →  指定ショップの商品を Shopify Admin API から同期
GET  /products             →  DB 内の商品一覧を返す
PUT  /products/{product_id}/margin  →  粗利率を手動で上書き
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.db.session import get_db, get_db_dep
from src.shopify.admin_api import sync_products_to_db

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/sync")
async def sync_products(
    shop_domain: str = Query(..., description="Shopify ショップドメイン"),
    db=Depends(get_db_dep),
):
    """
    Shopify Admin API から商品・在庫・価格を取得して products テーブルに同期する。
    """
    shop = await db.fetchrow(
        "SELECT access_token FROM shops WHERE shop_domain = $1 AND active = true",
        shop_domain,
    )
    if not shop:
        raise HTTPException(status_code=404, detail="shop not found or inactive")

    result = await sync_products_to_db(db, shop_domain, shop["access_token"])
    return {"status": "ok", **result}


@router.get("")
async def list_products(
    shop_domain: str = Query(...),
    limit: int = Query(50, ge=1, le=250),
    offset: int = Query(0, ge=0),
    db=Depends(get_db_dep),
):
    """
    DB 内の商品一覧を返す（粗利率・在庫順にソート）。
    """
    rows = await db.fetch(
        """
        SELECT product_id, title, price, gross_margin, stock_qty, accept_rate, updated_at
        FROM products
        WHERE shop_domain = $1
        ORDER BY gross_margin DESC, stock_qty DESC
        LIMIT $2 OFFSET $3
        """,
        shop_domain, limit, offset,
    )
    return [dict(r) for r in rows]


class MarginUpdate(BaseModel):
    gross_margin: float


@router.put("/{product_id}/margin")
async def update_margin(
    product_id: str,
    shop_domain: str = Query(...),
    body: MarginUpdate = ...,
    db=Depends(get_db_dep),
):
    """
    商品の粗利率を手動で上書きする（Shopify に cost が登録されていない場合に使用）。
    """
    if not (0 <= body.gross_margin <= 100):
        raise HTTPException(status_code=422, detail="gross_margin must be 0-100")

    result = await db.execute(
        """
        UPDATE products SET gross_margin = $1, updated_at = NOW()
        WHERE shop_domain = $2 AND product_id = $3
        """,
        body.gross_margin, shop_domain, product_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="product not found")

    return {"product_id": product_id, "gross_margin": body.gross_margin, "status": "updated"}
