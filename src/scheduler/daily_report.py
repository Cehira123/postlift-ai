"""
日次レポート スケジューラー
APScheduler を使い毎朝 9:00 JST に全ショップの前日サマリーをメール送信。
"""
import asyncio
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.db.session import get_db

scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")


async def _send_daily_reports() -> None:
    async with get_db() as db:
        shops = await db.fetch("SELECT shop_domain, owner_email FROM shops WHERE active = true")

    for shop in shops:
        await _report_for_shop(shop["shop_domain"], shop["owner_email"])


async def _report_for_shop(shop_domain: str, email: str) -> None:
    """
    前日のアップセル実績を集計してメール送信 (SendGrid / SES)。
    TODO: メール送信ロジックを実装する
    """
    print(f"[report] {shop_domain} → {email}")


@scheduler.scheduled_job("cron", hour=9, minute=0)
def run_daily_reports():
    asyncio.run(_send_daily_reports())


if __name__ == "__main__":
    scheduler.start()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
