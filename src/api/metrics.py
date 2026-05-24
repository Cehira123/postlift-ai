"""
メトリクス API
GET /metrics/summary  →  ショップ別の売上・承諾率サマリーを返す
"""
from fastapi import APIRouter, Depends

from src.db.session import get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary")
async def get_summary(shop_domain: str, db=Depends(get_db)):
    """
    直近30日間のアップセル承諾率・追加売上を集計して返す。
    """
    query = """
        SELECT
            COUNT(*)                                           AS total_offers,
            SUM(CASE WHEN accepted THEN 1 ELSE 0 END)         AS accepted_offers,
            ROUND(AVG(CASE WHEN accepted THEN 1.0 ELSE 0 END) * 100, 1) AS accept_rate_pct,
            COALESCE(SUM(CASE WHEN accepted THEN upsell_price ELSE 0 END), 0) AS extra_revenue
        FROM upsell_offers
        WHERE shop_domain = $1
          AND created_at >= NOW() - INTERVAL '30 days'
    """
    row = await db.fetchrow(query, shop_domain)
    return dict(row) if row else {}
