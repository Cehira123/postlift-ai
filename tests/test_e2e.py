"""
エンドツーエンドテスト
注文 → Webhook受信 → AIオファー生成 → DB保存 → メトリクス確認
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app

TEST_SHOP = "e2e-test-shop.myshopify.com"
TEST_SECRET = "e2e-test-webhook-secret-123"
TEST_PRODUCT_ID = "e2e-prod-001"


def make_hmac(secret: str, body: bytes) -> str:
    """アプリと同じロジックでHMAC署名を生成"""
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return base64.b64encode(digest.encode()).decode()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def db_pool():
    database_url = os.getenv("DATABASE_URL", "postgresql://localhost/postlift")
    pool = await asyncpg.create_pool(database_url, min_size=1, max_size=3)
    yield pool
    await pool.close()


@pytest_asyncio.fixture(scope="module", autouse=True)
async def seed_db(db_pool):
    """テスト用データを挿入し、テスト後にクリーンアップ"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO shops (shop_domain, access_token, active, plan)
            VALUES ($1, 'e2e_test_token', true, 'growth')
            ON CONFLICT (shop_domain) DO UPDATE SET active = true
            """,
            TEST_SHOP,
        )
        await conn.execute(
            """
            INSERT INTO products
                (shop_domain, product_id, title, price, gross_margin, stock_qty, accept_rate)
            VALUES ($1, $2, 'プレミアムコーヒー豆 500g', 3500.00, 65.0, 50, 0.45)
            ON CONFLICT (shop_domain, product_id) DO UPDATE
                SET gross_margin = 65.0, stock_qty = 50
            """,
            TEST_SHOP,
            TEST_PRODUCT_ID,
        )

    yield

    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM upsell_offers WHERE shop_domain = $1", TEST_SHOP
        )
        await conn.execute(
            "DELETE FROM products WHERE shop_domain = $1", TEST_SHOP
        )
        await conn.execute(
            "DELETE FROM billing WHERE shop_domain = $1", TEST_SHOP
        )
        await conn.execute(
            "DELETE FROM shops WHERE shop_domain = $1", TEST_SHOP
        )


@pytest_asyncio.fixture
async def client():
    """FastAPI ASGIテストクライアント"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


# ──────────────────────────────────────────────────────────────
# Step 1: ヘルスチェック
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step1_health_check(client):
    """ステップ1: APIサーバーが正常に起動・応答していること"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    print("\n✅ Step 1 PASS: ヘルスチェック OK")


# ──────────────────────────────────────────────────────────────
# Step 2: Webhook → オファー生成 → DB保存
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step2_webhook_creates_offer(client, db_pool):
    """ステップ2: 注文WebhookでAIオファーが生成・保存されること"""
    order_payload = {
        "id": 9990001,
        "line_items": [
            {"product_id": "other-product-999", "title": "有機緑茶 100g"}
        ],
    }
    body = json.dumps(order_payload).encode()
    hmac_header = make_hmac(TEST_SECRET, body)

    mock_choice = MagicMock()
    mock_choice.message.content = "一緒にいかがですか？"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("src.api.shopify_webhook.SHOPIFY_WEBHOOK_SECRET", TEST_SECRET), \
         patch("openai.ChatCompletion.acreate", new=AsyncMock(return_value=mock_response)):

        resp = await client.post(
            "/webhooks/orders/paid",
            content=body,
            headers={
                "X-Shopify-Hmac-Sha256": hmac_header,
                "X-Shopify-Shop-Domain": TEST_SHOP,
                "Content-Type": "application/json",
            },
        )

    assert resp.status_code == 200, f"Webhook failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "queued", f"Unexpected status: {data}"
    assert data["offer_id"] is not None, "offer_id が None"

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM upsell_offers WHERE shop_domain = $1 ORDER BY created_at DESC LIMIT 1",
            TEST_SHOP,
        )

    assert row is not None, "オファーがDBに保存されていない"
    assert row["product_id"] == TEST_PRODUCT_ID
    assert float(row["gross_margin"]) == pytest.approx(65.0)
    assert row["ai_score"] is not None
    assert float(row["ai_score"]) > 0.0
    print(f"\n✅ Step 2 PASS: オファー生成・保存 OK (offer_id={data['offer_id']}, score={float(row['ai_score']):.4f})")


# ──────────────────────────────────────────────────────────────
# Step 3: HMAC検証 — 不正なシグネチャは拒否
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step3_invalid_hmac_rejected(client):
    """ステップ3: 不正なHMACで送られたWebhookは401で拒否されること"""
    body = json.dumps({"id": 9990002, "line_items": []}).encode()

    with patch("src.api.shopify_webhook.SHOPIFY_WEBHOOK_SECRET", TEST_SECRET):
        resp = await client.post(
            "/webhooks/orders/paid",
            content=body,
            headers={
                "X-Shopify-Hmac-Sha256": "invalid-signature",
                "X-Shopify-Shop-Domain": TEST_SHOP,
                "Content-Type": "application/json",
            },
        )

    assert resp.status_code == 401
    print("\n✅ Step 3 PASS: 不正HMAC → 401 拒否 OK")


# ──────────────────────────────────────────────────────────────
# Step 4: 候補なしの場合
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step4_no_candidates(client):
    """ステップ4: 注文済み商品のみで候補なし → offer_id=None"""
    order_payload = {
        "id": 9990003,
        "line_items": [
            {"product_id": TEST_PRODUCT_ID, "title": "プレミアムコーヒー豆 500g"}
        ],
    }
    body = json.dumps(order_payload).encode()
    hmac_header = make_hmac(TEST_SECRET, body)

    with patch("src.api.shopify_webhook.SHOPIFY_WEBHOOK_SECRET", TEST_SECRET), \
         patch("openai.ChatCompletion.acreate", new=AsyncMock(return_value=MagicMock())):

        resp = await client.post(
            "/webhooks/orders/paid",
            content=body,
            headers={
                "X-Shopify-Hmac-Sha256": hmac_header,
                "X-Shopify-Shop-Domain": TEST_SHOP,
                "Content-Type": "application/json",
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["offer_id"] is None
    print("\n✅ Step 4 PASS: 候補なし → offer_id=None OK")


# ──────────────────────────────────────────────────────────────
# Step 5: メトリクス集計
# ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_step5_upsell_respond_accept(client, db_pool):
    """ステップ5: オファー承諾を記録 → DBに accepted=true が保存される"""
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id_str FROM upsell_offers WHERE shop_domain = $1 ORDER BY created_at DESC LIMIT 1",
            TEST_SHOP,
        )
    assert row is not None, "Step2でオファーが作成されていない"
    offer_id = row["id_str"]

    resp = await client.post(
        "/webhooks/upsell/respond",
        json={"offer_id": offer_id, "accepted": True},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["offer_id"] == offer_id
    assert data["accepted"] is True
    assert data["status"] == "recorded"

    async with db_pool.acquire() as conn:
        updated = await conn.fetchrow(
            "SELECT accepted, responded_at FROM upsell_offers WHERE id_str = $1",
            offer_id,
        )
    assert updated["accepted"] is True
    assert updated["responded_at"] is not None
    print(f"\n✅ Step 5 PASS: 承諾記録 OK (offer_id={offer_id})")


@pytest.mark.asyncio
async def test_step6_upsell_respond_reject(client, db_pool):
    """ステップ6: オファー拒否を記録 → DBに accepted=false が保存される"""
    order_payload = {
        "id": 9990004,
        "line_items": [{"product_id": "other-prod-888", "title": "抹茶ラテ"}],
    }
    body = json.dumps(order_payload).encode()
    hmac_header = make_hmac(TEST_SECRET, body)

    mock_choice = MagicMock()
    mock_choice.message.content = "ぜひ試してみてください"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("src.api.shopify_webhook.SHOPIFY_WEBHOOK_SECRET", TEST_SECRET), \
         patch("openai.ChatCompletion.acreate", new=AsyncMock(return_value=mock_response)):
        resp = await client.post(
            "/webhooks/orders/paid",
            content=body,
            headers={
                "X-Shopify-Hmac-Sha256": hmac_header,
                "X-Shopify-Shop-Domain": TEST_SHOP,
                "Content-Type": "application/json",
            },
        )
    assert resp.status_code == 200
    new_offer_id = resp.json()["offer_id"]
    assert new_offer_id is not None

    resp = await client.post(
        "/webhooks/upsell/respond",
        json={"offer_id": new_offer_id, "accepted": False},
    )
    assert resp.status_code == 200
    assert resp.json()["accepted"] is False

    async with db_pool.acquire() as conn:
        updated = await conn.fetchrow(
            "SELECT accepted FROM upsell_offers WHERE id_str = $1", new_offer_id
        )
    assert updated["accepted"] is False
    print(f"\n✅ Step 6 PASS: 拒否記録 OK (offer_id={new_offer_id})")


@pytest.mark.asyncio
async def test_step7_respond_not_found(client):
    """ステップ7: 存在しないoffer_idは404を返す"""
    resp = await client.post(
        "/webhooks/upsell/respond",
        json={"offer_id": "00000000-0000-0000-0000-000000000000", "accepted": True},
    )
    assert resp.status_code == 404
    print("\n✅ Step 7 PASS: 不明offer_id → 404 OK")


@pytest.mark.asyncio
async def test_step8_metrics_summary(client, db_pool):
    """ステップ8: 承諾・拒否混在時のメトリクスAPIが正しい集計を返すこと"""
    resp = await client.get("/metrics/summary", params={"shop_domain": TEST_SHOP})
    assert resp.status_code == 200
    data = resp.json()

    total = int(data["total_offers"])
    accepted = int(data["accepted_offers"])
    assert total >= 2
    assert 0 < accepted < total
    assert float(data["extra_revenue"]) > 0
    print(
        f"\n✅ Step 8 PASS: メトリクス OK "
        f"(total={total}, accepted={accepted}, "
        f"accept_rate={data['accept_rate_pct']}%, "
        f"revenue=¥{data['extra_revenue']})"
    )
