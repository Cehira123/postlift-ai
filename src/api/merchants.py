"""
マーチャント設定 API
GET  /merchants/{shop_domain}          →  設定を取得
PUT  /merchants/{shop_domain}/settings →  粗利閾値・在庫閾値を更新
GET  /merchants/{shop_domain}/kpi      →  KPIスナップショット履歴を返す
"""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.db.session import get_db_dep

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("/{shop_domain}")
async def get_merchant(shop_domain: str, db=Depends(get_db_dep)):
    """マーチャント設定を返す（未作成なら自動作成）"""
    row = await db.fetchrow(
        "SELECT * FROM merchants WHERE shop_domain = $1", shop_domain
    )
    if not row:
        shop = await db.fetchrow(
            "SELECT shop_domain FROM shops WHERE shop_domain = $1", shop_domain
        )
        if not shop:
            raise HTTPException(status_code=404, detail="shop not found")
        await db.execute(
            """
            INSERT INTO merchants (shop_domain)
            VALUES ($1)
            ON CONFLICT (shop_domain) DO NOTHING
            """,
            shop_domain,
        )
        row = await db.fetchrow(
            "SELECT * FROM merchants WHERE shop_domain = $1", shop_domain
        )
    return dict(row)


class MerchantSettings(BaseModel):
    margin_threshold: float | None = None
    stock_threshold: int | None = None
    plan: str | None = None
    owner_email: str | None = None


@router.put("/{shop_domain}/settings")
async def update_settings(
    shop_domain: str,
    body: MerchantSettings,
    db=Depends(get_db_dep),
):
    """
    粗利閾値・在庫閾値・プランを更新する。
    margin_threshold: 0.0〜1.0（例: 0.30 = 粗利30%未満は除外）
    """
    updates = []
    values = []
    idx = 1

    if body.margin_threshold is not None:
        if not (0.0 <= body.margin_threshold <= 1.0):
            raise HTTPException(status_code=422, detail="margin_threshold must be 0.0-1.0")
        updates.append(f"margin_threshold = ${idx}")
        values.append(body.margin_threshold)
        idx += 1

    if body.stock_threshold is not None:
        if body.stock_threshold < 0:
            raise HTTPException(status_code=422, detail="stock_threshold must be >= 0")
        updates.append(f"stock_threshold = ${idx}")
        values.append(body.stock_threshold)
        idx += 1

    if body.plan is not None:
        if body.plan not in ("starter", "growth", "scale"):
            raise HTTPException(status_code=422, detail="plan must be starter/growth/scale")
        updates.append(f"plan = ${idx}")
        values.append(body.plan)
        idx += 1

    if body.owner_email is not None:
        updates.append(f"updated_at = NOW()")
        await db.execute(
            f"UPDATE shops SET owner_email = ${idx} WHERE shop_domain = ${idx+1}",
            body.owner_email, shop_domain,
        )

    if not updates:
        raise HTTPException(status_code=422, detail="no fields to update")

    updates.append("updated_at = NOW()")
    values.append(shop_domain)
    query = f"UPDATE merchants SET {', '.join(updates)} WHERE shop_domain = ${idx}"
    await db.execute(query, *values)

    row = await db.fetchrow("SELECT * FROM merchants WHERE shop_domain = $1", shop_domain)
    return dict(row)


@router.get("/{shop_domain}/kpi")
async def get_kpi_history(
    shop_domain: str,
    days: int = 30,
    db=Depends(get_db_dep),
):
    """過去N日間のKPIスナップショット履歴を返す"""
    rows = await db.fetch(
        """
        SELECT snapshot_date, total_offers, accepted_offers,
               accept_rate_pct, extra_revenue
        FROM kpi_snapshots
        WHERE shop_domain = $1
          AND snapshot_date >= CURRENT_DATE - $2::int
        ORDER BY snapshot_date DESC
        """,
        shop_domain, days,
    )
    return [dict(r) for r in rows]
