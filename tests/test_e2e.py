import base64
import hashlib
import hmac
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient

from src.api import shopify_webhook
from src.api.main import app
from src.db.session import get_db_dep


TEST_SHOP = "e2e-test.myshopify.com"
TEST_SECRET = "e2e-secret"


def shopify_hmac(body: bytes) -> str:
    digest = hmac.new(TEST_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


class FakeDb:
    def __init__(self):
        self.products = {
            "variant-200": {
                "product_id": "variant-200",
                "title": "Launch Coffee - Dark roast",
                "price": 25.0,
                "gross_margin": 60.0,
                "stock_qty": 9,
                "accept_rate": 0.42,
            }
        }
        self.offers = {}
        self.ab_experiments = []

    async def fetch(self, query, *args):
        if "FROM products" in query and "product_id != ALL" in query:
            shop_domain, ordered_ids, margin_threshold = args
            if shop_domain != TEST_SHOP:
                return []
            return [
                product
                for product in self.products.values()
                if product["product_id"] not in ordered_ids
                and product["gross_margin"] >= margin_threshold
                and product["stock_qty"] > 0
            ]
        return []

    async def fetchrow(self, query, *args):
        if "SELECT margin_threshold FROM merchants" in query:
            return {"margin_threshold": 0.30}
        if "SELECT o.id_str" in query and "WHERE o.order_id" in query:
            order_id, shop_domain = args
            for offer in self.offers.values():
                if offer["order_id"] == order_id and offer["shop_domain"] == shop_domain:
                    product = self.products[offer["product_id"]]
                    return {**offer, "title": product["title"]}
            return None
        if "SELECT id FROM upsell_offers WHERE id_str" in query:
            offer = self.offers.get(args[0])
            return {"id": 1} if offer else None
        return None

    async def execute(self, query, *args):
        if "INSERT INTO upsell_offers" in query:
            (
                offer_id,
                shop_domain,
                order_id,
                product_id,
                upsell_price,
                gross_margin,
                stock_qty,
                ai_score,
                ab_variant,
                customer_id,
                copy_text,
            ) = args
            self.offers[offer_id] = {
                "id_str": offer_id,
                "shop_domain": shop_domain,
                "order_id": order_id,
                "product_id": product_id,
                "upsell_price": upsell_price,
                "gross_margin": gross_margin,
                "stock_qty": stock_qty,
                "ai_score": ai_score,
                "ab_variant": ab_variant,
                "customer_id": customer_id,
                "copy_text": copy_text,
                "accepted": None,
                "responded_at": None,
            }
            return "INSERT 0 1"
        if "INSERT INTO ab_experiments" in query:
            self.ab_experiments.append(
                {"shop_domain": args[0], "variant": args[1], "offer_id": args[2], "converted": None}
            )
            return "INSERT 0 1"
        if "UPDATE upsell_offers SET accepted" in query:
            accepted, responded_at, offer_id = args
            self.offers[offer_id]["accepted"] = accepted
            self.offers[offer_id]["responded_at"] = responded_at
            return "UPDATE 1"
        if "UPDATE ab_experiments SET converted" in query:
            accepted, offer_id = args
            for experiment in self.ab_experiments:
                if experiment["offer_id"] == offer_id and experiment["converted"] is None:
                    experiment["converted"] = accepted
            return "UPDATE 1"
        return "UPDATE 0"


@pytest.fixture
def fake_db(monkeypatch):
    db = FakeDb()

    @asynccontextmanager
    async def fake_get_db():
        yield db

    async def fake_get_db_dep():
        yield db

    monkeypatch.setattr(shopify_webhook, "SHOPIFY_WEBHOOK_SECRET", TEST_SECRET)
    monkeypatch.setattr(shopify_webhook, "get_db", fake_get_db)
    app.dependency_overrides[get_db_dep] = fake_get_db_dep
    yield db
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_purchase_offer_lifecycle_e2e(fake_db):
    order_body = b'{"id": "order-100", "line_items": [{"product_id": "already-bought", "title": "Starter beans"}]}'
    headers = {
        "X-Shopify-Hmac-Sha256": shopify_hmac(order_body),
        "X-Shopify-Shop-Domain": TEST_SHOP,
        "Content-Type": "application/json",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        webhook = await client.post("/webhooks/orders/paid", content=order_body, headers=headers)
        assert webhook.status_code == 200
        offer_id = webhook.json()["offer_id"]
        assert offer_id

        current = await client.get(
            "/offers/current",
            params={"order_id": "order-100", "shop_domain": TEST_SHOP},
        )
        assert current.status_code == 200
        assert current.json()["variant_id"] == "variant-200"
        assert current.json()["copy_text"]

        response = await client.post(
            "/webhooks/upsell/respond",
            json={"offer_id": offer_id, "accepted": True},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "recorded"

    assert fake_db.offers[offer_id]["accepted"] is True
    assert fake_db.ab_experiments[0]["converted"] is True
