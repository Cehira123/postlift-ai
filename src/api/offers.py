"""
オファー取得 API
GET /offers/current  →  注文IDに紐づく現在のオファーを返す（Shopify Extension から呼ぶ）
GET /offers/{offer_id}  →  オファー詳細を返す
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.session import get_db_dep

router = APIRouter(prefix="/offers", tags=["offers"])


@router.get("/current")
async def get_current_offer(
    order_id: str = Query(..., description="Shopify Order ID"),
    shop_domain: str = Query(...),
    db=Depends(get_db_dep),
):
    """
    注文完了直後に Shopify Post-Purchase Extension から呼ばれる。
    該当注文に紐づく最新オファーを返す。
    """
    row = await db.fetchrow(
        """
        SELECT o.id_str, o.product_id, o.upsell_price, o.ai_score,
               o.copy_text, o.ab_variant,
               p.title, p.gross_margin
        FROM upsell_offers o
        LEFT JOIN products p
               ON o.product_id = p.product_id AND o.shop_domain = p.shop_domain
        WHERE o.order_id = $1 AND o.shop_domain = $2
        ORDER BY o.created_at DESC
        LIMIT 1
        """,
        order_id, shop_domain,
    )
    if not row:
        raise HTTPException(status_code=404, detail="no offer for this order")

    return {
        "offer_id": row["id_str"],
        "product_id": row["product_id"],
        "variant_id": row["product_id"],
        "title": row["title"],
        "price": float(row["upsell_price"]),
        "ai_score": float(row["ai_score"]) if row["ai_score"] else None,
        "copy_text": row["copy_text"],
        "ab_variant": row["ab_variant"],
    }


@router.get("/{offer_id}")
async def get_offer(offer_id: str, db=Depends(get_db_dep)):
    """オファー詳細（AI生成コピー含む）を返す"""
    row = await db.fetchrow(
        """
        SELECT o.id_str, o.shop_domain, o.order_id, o.product_id,
               o.upsell_price, o.gross_margin, o.stock_qty,
               o.accepted, o.ai_score, o.created_at, o.responded_at,
               p.title
        FROM upsell_offers o
        LEFT JOIN products p
               ON o.product_id = p.product_id AND o.shop_domain = p.shop_domain
        WHERE o.id_str = $1
        """,
        offer_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="offer not found")

    return dict(row)
