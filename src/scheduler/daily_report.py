"""
日次レポート & KPI スナップショット スケジューラー
APScheduler を使い毎朝 9:00 JST に:
  1. 全ショップの前日 KPI を kpi_snapshots テーブルに保存
  2. 承諾率が低い商品の accept_rate を更新（自動抑制）
  3. オーナーへ KPI メール送信
"""
import asyncio
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.db.session import get_db
from src.notifications.email import send_kpi_email

scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")


async def take_kpi_snapshot(db, shop_domain: str) -> dict:
    """前日の KPI を集計して kpi_snapshots に upsert する"""
    yesterday = date.today() - timedelta(days=1)
    row = await db.fetchrow(
        """
        SELECT
            COUNT(*)                                                     AS total_offers,
            SUM(CASE WHEN accepted THEN 1 ELSE 0 END)                   AS accepted_offers,
            ROUND(AVG(CASE WHEN accepted THEN 1.0 ELSE 0 END) * 100, 1) AS accept_rate_pct,
            COALESCE(SUM(CASE WHEN accepted THEN upsell_price ELSE 0 END), 0) AS extra_revenue
        FROM upsell_offers
        WHERE shop_domain = $1 AND created_at::date = $2
        """,
        shop_domain, yesterday,
    )

    snapshot = {
        "total_offers":    int(row["total_offers"]),
        "accepted_offers": int(row["accepted_offers"]),
        "accept_rate_pct": float(row["accept_rate_pct"] or 0),
        "extra_revenue":   float(row["extra_revenue"]),
    }

    await db.execute(
        """
        INSERT INTO kpi_snapshots
            (shop_domain, snapshot_date, total_offers, accepted_offers,
             accept_rate_pct, extra_revenue)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (shop_domain, snapshot_date) DO UPDATE SET
            total_offers    = EXCLUDED.total_offers,
            accepted_offers = EXCLUDED.accepted_offers,
            accept_rate_pct = EXCLUDED.accept_rate_pct,
            extra_revenue   = EXCLUDED.extra_revenue
        """,
        shop_domain, yesterday,
        snapshot["total_offers"], snapshot["accepted_offers"],
        snapshot["accept_rate_pct"], snapshot["extra_revenue"],
    )
    return snapshot


async def suppress_low_accept_rate(db, shop_domain: str) -> int:
    """
    過去 30 日間の商品ごとの承諾率を再計算して products.accept_rate を更新する。
    承諾率が低い商品は自動的に accept_rate が下がり、次回スコアリングで優先度が下がる。
    """
    result = await db.execute(
        """
        UPDATE products p
        SET accept_rate = subq.rate
        FROM (
            SELECT
                product_id,
                ROUND(
                    SUM(CASE WHEN accepted THEN 1.0 ELSE 0 END)
                    / NULLIF(COUNT(*), 0), 4
                ) AS rate
            FROM upsell_offers
            WHERE shop_domain = $1
              AND created_at >= NOW() - INTERVAL '30 days'
              AND accepted IS NOT NULL
            GROUP BY product_id
        ) subq
        WHERE p.shop_domain = $1 AND p.product_id = subq.product_id
        """,
        shop_domain,
    )
    try:
        return int((result or "UPDATE 0").split()[-1])
    except (ValueError, IndexError):
        return 0


async def _run_daily_reports() -> None:
    async with get_db() as db:
        shops = await db.fetch(
            "SELECT shop_domain, owner_email FROM shops WHERE active = true"
        )

    for shop in shops:
        shop_domain = shop["shop_domain"]
        email = shop["owner_email"]
        try:
            async with get_db() as db:
                snapshot = await take_kpi_snapshot(db, shop_domain)
                updated = await suppress_low_accept_rate(db, shop_domain)

            print(
                f"[daily_report] {shop_domain} | "
                f"offers={snapshot['total_offers']}, "
                f"accept={snapshot['accept_rate_pct']}%, "
                f"revenue={snapshot['extra_revenue']}, "
                f"products_updated={updated}"
            )

            if email:
                await send_kpi_email(email, shop_domain, snapshot)

        except Exception as e:
            print(f"[daily_report] ERROR {shop_domain}: {e}")


@scheduler.scheduled_job("cron", hour=9, minute=0, id="daily_report")
def _scheduled_job() -> None:
    asyncio.run(_run_daily_reports())


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
