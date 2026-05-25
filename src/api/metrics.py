"""
メトリクス API
GET /metrics/summary     → ショップ別 30 日間サマリー
GET /metrics/trend       → 日次承諾率・売上トレンド（最大 90 日）
GET /metrics/products    → 商品別オファー成績ランキング
"""
from fastapi import APIRouter, Depends, Query

from src.db.session import get_db_dep

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/summary")
async def get_summary(shop_domain: str, db=Depends(get_db_dep)):
    """直近30日間のアップセル承諾率・追加売上を集計して返す"""
    row = await db.fetchrow(
        """
        SELECT
            COUNT(*)                                                     AS total_offers,
            SUM(CASE WHEN accepted THEN 1 ELSE 0 END)                   AS accepted_offers,
            ROUND(AVG(CASE WHEN accepted THEN 1.0 ELSE 0 END) * 100, 1) AS accept_rate_pct,
            COALESCE(SUM(CASE WHEN accepted THEN upsell_price ELSE 0 END), 0) AS extra_revenue
        FROM upsell_offers
        WHERE shop_domain = $1
          AND created_at >= NOW() - INTERVAL '30 days'
        """,
        shop_domain,
    )
    return dict(row) if row else {}


@router.get("/trend")
async def get_trend(
    shop_domain: str,
    days: int = Query(30, ge=1, le=90),
    db=Depends(get_db_dep),
):
    """
    日次の承諾率・売上トレンドを返す（Chart.js 用）。
    KPI スナップショットから取得し、なければ upsell_offers から直接集計する。
    """
    rows = await db.fetch(
        """
        SELECT
            snapshot_date::text                AS date,
            total_offers,
            accepted_offers,
            accept_rate_pct,
            extra_revenue
        FROM kpi_snapshots
        WHERE shop_domain = $1
          AND snapshot_date >= CURRENT_DATE - $2::int
        ORDER BY snapshot_date ASC
        """,
        shop_domain, days,
    )

    if not rows:
        # スナップショットがまだない場合は生データから集計
        rows = await db.fetch(
            """
            SELECT
                created_at::date::text                                          AS date,
                COUNT(*)                                                        AS total_offers,
                SUM(CASE WHEN accepted THEN 1 ELSE 0 END)                      AS accepted_offers,
                ROUND(AVG(CASE WHEN accepted THEN 1.0 ELSE 0 END) * 100, 1)    AS accept_rate_pct,
                COALESCE(SUM(CASE WHEN accepted THEN upsell_price ELSE 0 END), 0) AS extra_revenue
            FROM upsell_offers
            WHERE shop_domain = $1
              AND created_at >= NOW() - ($2 || ' days')::INTERVAL
            GROUP BY created_at::date
            ORDER BY created_at::date ASC
            """,
            shop_domain, str(days),
        )

    return [dict(r) for r in rows]


@router.get("/products")
async def get_product_metrics(
    shop_domain: str,
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db=Depends(get_db_dep),
):
    """
    商品別のオファー成績ランキングを返す。
    承諾率・追加売上・表示回数で評価。
    """
    rows = await db.fetch(
        """
        SELECT
            o.product_id,
            COALESCE(p.title, o.product_id)                             AS title,
            COUNT(*)                                                     AS total_offers,
            SUM(CASE WHEN o.accepted THEN 1 ELSE 0 END)                 AS accepted_offers,
            ROUND(
                SUM(CASE WHEN o.accepted THEN 1.0 ELSE 0 END)
                / NULLIF(COUNT(*), 0) * 100, 1
            )                                                            AS accept_rate_pct,
            COALESCE(
                SUM(CASE WHEN o.accepted THEN o.upsell_price ELSE 0 END), 0
            )                                                            AS extra_revenue,
            ROUND(AVG(o.ai_score), 4)                                   AS avg_ai_score
        FROM upsell_offers o
        LEFT JOIN products p
               ON o.product_id = p.product_id AND o.shop_domain = p.shop_domain
        WHERE o.shop_domain = $1
          AND o.created_at >= NOW() - ($2 || ' days')::INTERVAL
        GROUP BY o.product_id, p.title
        ORDER BY extra_revenue DESC
        LIMIT $3
        """,
        shop_domain, str(days), limit,
    )
    return [dict(r) for r in rows]
