"""
デモ・シードデータ API
POST /demo/seed  →  ダッシュボード確認用のサンプルデータを投入する
"""
import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from src.db.session import get_db_dep

router = APIRouter(prefix="/demo", tags=["demo"])

DEMO_PRODUCTS = [
    {"product_id": "demo-001", "title": "プレミアム保湿クリーム 200ml", "price": 3800, "gross_margin": 62, "stock_qty": 120},
    {"product_id": "demo-002", "title": "ビタミンC美容液 30ml",         "price": 5200, "gross_margin": 71, "stock_qty": 85},
    {"product_id": "demo-003", "title": "日焼け止めSPF50 80g",          "price": 2400, "gross_margin": 55, "stock_qty": 200},
    {"product_id": "demo-004", "title": "コラーゲン洗顔フォーム",       "price": 1800, "gross_margin": 48, "stock_qty": 150},
    {"product_id": "demo-005", "title": "敏感肌用化粧水 150ml",         "price": 4200, "gross_margin": 65, "stock_qty": 60},
]


@router.post("/seed", summary="デモデータ投入（開発・テスト用）")
async def seed_demo_data(
    shop_domain: str = Query("demo.myshopify.com"),
    days: int = Query(30, ge=7, le=90, description="過去何日分のデータを生成するか"),
    db=Depends(get_db_dep),
):
    """
    ダッシュボード動作確認用のサンプルデータを投入します。\n
    - shops / merchants レコードを作成（なければ）
    - 商品 5 件を登録
    - 過去 N 日分のオファー履歴・A/B テストデータ・KPI スナップショットを生成\n
    ⚠️ 本番環境での使用は非推奨です。既存データは上書きされません。
    """
    # ── ショップ登録（なければ作成） ──
    existing = await db.fetchrow(
        "SELECT shop_domain FROM shops WHERE shop_domain = $1", shop_domain
    )
    if not existing:
        await db.execute(
            """
            INSERT INTO shops (shop_domain, access_token, active, owner_email)
            VALUES ($1, 'demo_token', true, 'demo@example.com')
            ON CONFLICT (shop_domain) DO NOTHING
            """,
            shop_domain,
        )

    await db.execute(
        """
        INSERT INTO merchants (shop_domain, margin_threshold, stock_threshold, plan)
        VALUES ($1, 0.30, 5, 'growth')
        ON CONFLICT (shop_domain) DO UPDATE
            SET plan = 'growth', updated_at = NOW()
        """,
        shop_domain,
    )

    # ── 商品登録 ──
    for p in DEMO_PRODUCTS:
        await db.execute(
            """
            INSERT INTO products (shop_domain, product_id, title, price, gross_margin, stock_qty, accept_rate)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (shop_domain, product_id) DO UPDATE
                SET title = $3, price = $4, gross_margin = $5, stock_qty = $6, updated_at = NOW()
            """,
            shop_domain, p["product_id"], p["title"],
            p["price"], p["gross_margin"], p["stock_qty"],
            round(random.uniform(0.10, 0.35), 4),
        )

    # ── オファー・A/B データ生成 ──
    now = datetime.now(timezone.utc)
    offers_created = 0
    ab_created = 0

    for day_offset in range(days, 0, -1):
        base_dt = now - timedelta(days=day_offset)
        # 1日あたり 3〜12 件のオファー
        n_offers = random.randint(3, 12)

        for _ in range(n_offers):
            product = random.choice(DEMO_PRODUCTS)
            variant = "A" if random.random() < 0.5 else "B"
            # バリアント B は承諾率が少し高い設定
            accept_prob = 0.22 if variant == "B" else 0.16
            accepted = random.random() < accept_prob

            offer_id = str(uuid.uuid4())
            created_at = base_dt + timedelta(
                hours=random.randint(9, 21),
                minutes=random.randint(0, 59),
            )
            responded_at = created_at + timedelta(seconds=random.randint(10, 120)) if accepted is not None else None
            ai_score = round(random.uniform(0.35, 0.85), 4)

            copy_texts = {
                "A": f"{product['title']}もセットでいかがですか？",
                "B": f"残りわずか！{product['title']}を今すぐ追加",
            }

            await db.execute(
                """
                INSERT INTO upsell_offers
                    (id_str, shop_domain, order_id, product_id, upsell_price,
                     gross_margin, stock_qty, accepted, ai_score, ab_variant,
                     copy_text, created_at, responded_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                ON CONFLICT (id_str) DO NOTHING
                """,
                offer_id, shop_domain,
                f"order-{random.randint(10000, 99999)}",
                product["product_id"],
                float(product["price"]),
                float(product["gross_margin"]),
                product["stock_qty"],
                accepted,
                ai_score,
                variant,
                copy_texts[variant],
                created_at,
                responded_at if accepted else None,
            )
            offers_created += 1

            # A/B テーブルにも記録
            await db.execute(
                """
                INSERT INTO ab_experiments
                    (shop_domain, experiment_name, variant, offer_id, converted, created_at)
                VALUES ($1, 'copy_variant', $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
                """,
                shop_domain, variant, offer_id, accepted, created_at,
            )
            ab_created += 1

    # ── 商品の accept_rate を実績から更新 ──
    await db.execute(
        """
        UPDATE products p
        SET accept_rate = sub.rate
        FROM (
            SELECT product_id,
                   ROUND(AVG(CASE WHEN accepted THEN 1.0 ELSE 0 END), 4) AS rate
            FROM upsell_offers
            WHERE shop_domain = $1
            GROUP BY product_id
        ) sub
        WHERE p.shop_domain = $1 AND p.product_id = sub.product_id
        """,
        shop_domain,
    )

    # ── KPI スナップショットを生成 ──
    snapshots_created = 0
    for day_offset in range(days, 0, -1):
        snap_date = (now - timedelta(days=day_offset)).date()

        row = await db.fetchrow(
            """
            SELECT
                COUNT(*)                                                     AS total_offers,
                SUM(CASE WHEN accepted THEN 1 ELSE 0 END)                   AS accepted_offers,
                ROUND(AVG(CASE WHEN accepted THEN 1.0 ELSE 0 END)*100, 2)   AS accept_rate_pct,
                COALESCE(SUM(CASE WHEN accepted THEN upsell_price ELSE 0 END),0) AS extra_revenue
            FROM upsell_offers
            WHERE shop_domain = $1 AND created_at::date = $2
            """,
            shop_domain, snap_date,
        )

        if row and int(row["total_offers"]) > 0:
            await db.execute(
                """
                INSERT INTO kpi_snapshots
                    (shop_domain, snapshot_date, total_offers, accepted_offers,
                     accept_rate_pct, extra_revenue)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (shop_domain, snapshot_date) DO UPDATE
                    SET total_offers    = $3,
                        accepted_offers = $4,
                        accept_rate_pct = $5,
                        extra_revenue   = $6
                """,
                shop_domain, snap_date,
                int(row["total_offers"]),
                int(row["accepted_offers"]),
                float(row["accept_rate_pct"] or 0),
                float(row["extra_revenue"] or 0),
            )
            snapshots_created += 1

    return {
        "message": (
            f"デモデータを投入しました: "
            f"商品 {len(DEMO_PRODUCTS)} 件、"
            f"オファー {offers_created} 件（{days} 日分）、"
            f"A/B レコード {ab_created} 件、"
            f"KPI スナップショット {snapshots_created} 件"
        ),
        "shop_domain": shop_domain,
        "products": len(DEMO_PRODUCTS),
        "offers": offers_created,
        "ab_records": ab_created,
        "kpi_snapshots": snapshots_created,
    }
