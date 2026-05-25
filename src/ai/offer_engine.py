"""
AI オファーエンジン v2
注文データ・在庫・粗利・顧客スコア・A/B テストを統合してオファーを生成する。
"""
from __future__ import annotations

import os
import random
import uuid
from typing import Any

from openai import AsyncOpenAI

from src.ai.customer_score import get_customer_score

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# スコアリングの重み
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
    """
    粗利率・在庫・過去承諾率・顧客 RFM スコアで 0〜1 のスコアを算出。
    """
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
    """
    DB からアップセル候補商品を取得。
    既に注文した商品は除外し、粗利 >= margin_threshold かつ在庫 > 0 のみ対象。
    """
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
    """マーチャント設定から粗利閾値を取得する（デフォルト 30%）"""
    row = await db.fetchrow(
        "SELECT margin_threshold FROM merchants WHERE shop_domain = $1",
        shop_domain,
    )
    if row:
        return float(row["margin_threshold"]) * 100  # 0.30 → 30
    return 30.0


async def _generate_copy(
    product_title: str,
    order_items: list[str],
    variant: str = "A",
) -> str:
    """
    GPT-4o-mini で訴求コピーを生成。
    バリアント A: 簡潔なベネフィット訴求
    バリアント B: 緊急性・希少性訴求
    """
    if variant == "B":
        tone = "在庫わずか・今だけの特別価格であることを強調した緊急性のある"
    else:
        tone = "主要なベネフィットを伝える自然で親しみやすい"

    prompt = (
        f"あなたは Shopify ストアのコンバージョン最適化の専門家です。\n"
        f"顧客は今 {', '.join(order_items)} を購入しました。\n"
        f"次の商品を追加購入するよう促す、{tone}日本語の一文を作成してください: {product_title}\n"
        f"※ 25文字以内、絵文字不可、体言止め可"
    )
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=60,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"{product_title}はいかがですか？"


async def build_offer(
    db,
    shop_domain: str,
    order: dict[str, Any],
) -> dict:
    """
    メイン関数。注文データを受け取り最適なオファーを生成して DB に保存。
    Returns: offer dict (offer_id, product_id, copy, price, score, ab_variant)
    """
    line_items = order.get("line_items", [])
    ordered_ids = [str(item["product_id"]) for item in line_items]
    ordered_titles = [item["title"] for item in line_items]
    customer_id = str(order.get("customer", {}).get("id", "")) or None

    # マーチャント設定から粗利閾値を取得
    margin_threshold = await _fetch_margin_threshold(db, shop_domain)

    candidates = await _fetch_candidates(db, shop_domain, ordered_ids, margin_threshold)
    if not candidates:
        return {"offer_id": None, "reason": "no_candidates"}

    # 顧客スコアを取得
    customer_rfm = 0.5
    if customer_id:
        customer_rfm = await get_customer_score(db, shop_domain, customer_id)

    # A/B バリアントをランダム割り当て
    ab_variant = "A" if random.random() < 0.5 else "B"

    # スコアリングして最上位を選択
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

    # A/B テーブルにも記録
    try:
        await db.execute(
            """
            INSERT INTO ab_experiments (shop_domain, experiment_name, variant, offer_id)
            VALUES ($1, 'copy_variant', $2, $3)
            """,
            shop_domain, ab_variant, offer_id,
        )
    except Exception:
        pass  # A/B 記録失敗はオファー生成を止めない

    return {
        "offer_id": offer_id,
        "product_id": best["product_id"],
        "title": best["title"],
        "price": float(best["price"]),
        "copy": copy_text,
        "score": score,
        "ab_variant": ab_variant,
    }
