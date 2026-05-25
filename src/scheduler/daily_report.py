"""
日次レポート & KPI スナップショット スケジューラー
APScheduler を使い毎朝 9:00 JST に:
  1. 全ショップの前日 KPI を kpi_snapshots テーブルに保存
  2. オーナーへメール送信（TODO: SendGrid / SES 連携）
  3. 承諾率が低いオファーの自動抑制（accept_rate を更新）
"""
import asyncio
import os
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.db.session import get_db

scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")


async def _take_kpi_snapshot(db, shop_domain: str) -> dict:
    """
    前日の KPI を集計して kpi_snapshots テーブルに upsert する。
    """
    yesterday = date.today() - timedelta(days=1)
    row = await db.fetchrow(
        """
        SELECT
            COUNT(*)                                                    AS total_offers,
            SUM(CASE WHEN accepted THEN 1 ELSE 0 END)                  AS accepted_offers,
            ROUND(AVG(CASE WHEN accepted THEN 1.0 ELSE 0 END) * 100, 1) AS accept_rate_pct,
            COALESCE(SUM(CASE WHEN accepted THEN upsell_price ELSE 0 END), 0) AS extra_revenue
        FROM upsell_offers
        WHERE shop_domain = $1
          AND created_at::date = $2
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
            (shop_domain, snapshot_date, total_offers, accepted_offers, accept_rate_pct, extra_revenue)
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


async def _suppress_low_accept_rate(db, shop_domain: str) -> int:
    """
    過去 30 日間の商品ごとの承諾率を再計算して products.accept_rate を更新する。
    承諾率が低い商品は自動的にスコアが下がり、提案頻度が減る。
    """
    result = await db.execute(
        """
        UPDATE products p
        SET accept_rate = subq.rate
        FROM (
            SELECT
                product_id,
                ROUND(
                    SUM(CASE WHEN accepted THEN 1.0 ELSE 0 END) / NULLIF(COUNT(*), 0),
                    4
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
    updated = int(result.split()[-1]) if result else 0
    return updated


async def _send_daily_reports() -> None:
    async with get_db() as db:
        shops = await db.fetch(
            "SELECT shop_domain, owner_email FROM shops WHERE active = true"
        )

    for shop in shops:
        shop_domain = shop["shop_domain"]
        email = shop["owner_email"]
        try:
            async with get_db() as db:
                snapshot = await _take_kpi_snapshot(db, shop_domain)
                updated = await _suppress_low_accept_rate(db, shop_domain)

            print(
                f"[daily_report] {shop_domain} | "
                f"offers={snapshot['total_offers']}, "
                f"accept={snapshot['accept_rate_pct']}%, "
                f"revenue={snapshot['extra_revenue']}, "
                f"accept_rate_updated={updated}"
            )

            if email:
                await _send_email(email, shop_domain, snapshot)

        except Exception as e:
            print(f"[daily_report] ERROR {shop_domain}: {e}")


async def _send_email(email: str, shop_domain: str, snapshot: dict) -> None:
    """
    前日の KPI サマリーをメール送信する。
    TODO: SendGrid / AWS SES SDK で実際に送信する
    """
    print(
        f"[email] TO={email} | {shop_domain} | "
        f"accept_rate={snapshot['accept_rate_pct']}% | "
        f"revenue={snapshot['extra_revenue']}"
    )


@scheduler.scheduled_job("cron", hour=9, minute=0)
def run_daily_reports():
    asyncio.run(_send_daily_reports())


if __name__ == "__main__":
    scheduler.start()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
