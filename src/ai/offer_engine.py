"""AI-assisted offer selection for post-purchase upsells."""
from __future__ import annotations

import os
import random
import uuid
from typing import Any

from openai import AsyncOpenAI

from src.ai.customer_score import get_customer_score

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

WEIGHT_MARGIN = 0.4
WEIGHT_STOCK = 0.2
WEIGHT_ACCEPT_RATE = 0.25
WEIGHT_CUSTOMER = 0.15


def _score(
    margin: float,
    stock: int,
    accept_rate: float,
    customer_rfm: float = 0.5,
) -> float:
    """Return a 0..1 ranking score from margin, stock, acceptance, and customer fit."""
    margin = max(0.0, min(float(margin), 1.0))
    stock = max(0, int(stock))
    accept_rate = max(0.0, min(float(accept_rate), 1.0))
    customer_rfm = max(0.0, min(float(customer_rfm), 1.0))
    stock_norm = min(stock, 100) / 100
    return (
        WEIGHT_MARGIN * margin
        + WEIGHT_STOCK * stock_norm
        + WEIGHT_ACCEPT_RATE * accept_rate
        + WEIGHT_CUSTOMER * customer_rfm
    )


async def _fetch_candidates(
    db, shop_domain: str, ordered_product_ids: list[str], margin_threshold: float = 30.0
) -> list[dict]:
    rows = await db.fetch(
        """
        SELECT product_id, title, price, gross_margin, stock_qty,
               COALESCE(accept_rate, 0) AS accept_rate
        FROM products
        WHERE shop_domain = $1
          AND product_id != ALL($2::text[])
          AND gross_margin >= $3
          AND stock_qty > 0
        ORDER BY gross_margin DESC
        LIMIT 20
        """,
        shop_domain,
        ordered_product_ids,
        margin_threshold,
    )
    return [dict(r) for r in rows]


async def _fetch_margin_threshold(db, shop_domain: str) -> float:
    row = await db.fetchrow(
        "SELECT margin_threshold FROM merchants WHERE shop_domain = $1",
        shop_domain,
    )
    if row:
        return float(row["margin_threshold"]) * 100
    return 30.0


async def _generate_copy(
    product_title: str,
    order_items: list[str],
    variant: str = "A",
) -> str:
    """Generate concise upsell copy, with a deterministic fallback."""
    fallback = f"Add {product_title} to this order today."
    if not os.getenv("OPENAI_API_KEY"):
        return fallback

    tone = "urgent but tasteful, mentioning limited availability" if variant == "B" else "friendly and benefit-led"
    prompt = (
        "You are writing Shopify post-purchase upsell copy.\n"
        f"The customer bought: {', '.join(order_items)}.\n"
        f"Offer this add-on product in Japanese with a {tone} tone: {product_title}\n"
        "Keep it under 35 Japanese characters. No emoji. No quotation marks."
    )
    try:
        response = await client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.7,
        )
        text = response.choices[0].message.content
        return text.strip() if text else fallback
    except Exception:
        return fallback


async def build_offer(
    db,
    shop_domain: str,
    order: dict[str, Any],
) -> dict:
    """Select, score, copywrite, and persist the best upsell offer."""
    line_items = order.get("line_items", [])
    ordered_ids = [str(item["product_id"]) for item in line_items if "product_id" in item]
    ordered_titles = [str(item.get("title", "purchased item")) for item in line_items]
    customer_id = str(order.get("customer", {}).get("id", "")) or None

    margin_threshold = await _fetch_margin_threshold(db, shop_domain)
    candidates = await _fetch_candidates(db, shop_domain, ordered_ids, margin_threshold)
    if not candidates:
        return {"offer_id": None, "reason": "no_candidates"}

    customer_rfm = 0.5
    if customer_id:
        customer_rfm = await get_customer_score(db, shop_domain, customer_id)

    ab_variant = "A" if random.random() < 0.5 else "B"
    best = max(
        candidates,
        key=lambda c: _score(
            float(c["gross_margin"]) / 100,
            int(c["stock_qty"]),
            float(c["accept_rate"]),
            customer_rfm,
        ),
    )
    score = _score(
        float(best["gross_margin"]) / 100,
        int(best["stock_qty"]),
        float(best["accept_rate"]),
        customer_rfm,
    )
    copy_text = await _generate_copy(best["title"], ordered_titles, ab_variant)
    offer_id = str(uuid.uuid4())

    await db.execute(
        """
        INSERT INTO upsell_offers
            (id_str, shop_domain, order_id, product_id, upsell_price,
             gross_margin, stock_qty, ai_score, ab_variant, customer_id, copy_text)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """,
        offer_id,
        shop_domain,
        str(order["id"]),
        best["product_id"],
        float(best["price"]),
        float(best["gross_margin"]),
        int(best["stock_qty"]),
        score,
        ab_variant,
        customer_id,
        copy_text,
    )

    try:
        await db.execute(
            """
            INSERT INTO ab_experiments (shop_domain, experiment_name, variant, offer_id)
            VALUES ($1, 'copy_variant', $2, $3)
            """,
            shop_domain,
            ab_variant,
            offer_id,
        )
    except Exception:
        pass

    return {
        "offer_id": offer_id,
        "product_id": best["product_id"],
        "title": best["title"],
        "price": float(best["price"]),
        "copy": copy_text,
        "score": score,
        "ab_variant": ab_variant,
    }
