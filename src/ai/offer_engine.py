"""
AI オファーエンジン
注文データ・在庫・粗利を元に最適なアップセル商品を選定し、
GPT-4o-mini でパーソナライズされた訴求文を生成する。
"""
from __future__ import annotations

import os
import uuid
from typing import Any

import openai

from src.db.session import get_db

openai.api_key = os.getenv("OPENAI_API_KEY", "")

# スコアリングの重み
WEIGHT_MARGIN = 0.5
WEIGHT_STOCK = 0.2
WEIGHT_ACCEPT_RATE = 0.3


def _score(margin: float, stock: int, accept_rate: float) -> float:
    """
    粗利率・在庫数・過去承諾率で 0-1 のスコアを算出。
    stock は 0-100 にクリップして正規化。
    """
    stock_norm = min(stock, 100) / 100
    return WEIGHT_MARGIN * margin + WEIGHT_STOCK * stock_norm + WEIGHT_ACCEPT_RATE * accept_rate


async def _fetch_candidates(
    db, shop_domain: str, ordered_product_ids: list[str]
) -> list[dict]:
    """
    DB からアップセル候補商品を取得。
    既に注文した商品は除外し、粗利 >= 30% かつ在庫 > 0 のみ対象。
    """
    rows = await db.fetch(
        """
        SELECT product_id, title, price, gross_margin, stock_qty,
               COALESCE(accept_rate, 0) AS accept_rate
        FROM products
        WHERE shop_domain = $1
          AND product_id != ALL($2::text[])
          AND gross_margin >= 30
          AND stock_qty > 0
        ORDER BY gross_margin DESC
        LIMIT 20
        """,
        shop_domain,
        ordered_product_ids,
    )
    return [dict(r) for r in rows]


async def _generate_copy(product_title: str, order_items: list[str]) -> str:
    """
    GPT-4o-mini で訴求コピーを生成。
    """
    prompt = (
        f"あなたは Shopify ストアのコンバージョン最適化の専門家です。\n"
        f"顧客は今 {', '.join(order_items)} を購入しました。\n"
        f"次の商品を追加購入するよう促す、自然で魅力的な日本語の一文を作成してください: {product_title}\n"
        f"※ 20文字以内、絵文字不可"
    )
    response = await openai.ChatCompletion.acreate(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=60,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


async def build_offer(
    db,
    shop_domain: str,
    order: dict[str, Any],
) -> dict:
    """
    メイン関数。注文データを受け取り最適なオファーを生成して DB に保存。
    Returns: offer dict (offer_id, product_id, copy, price, score)
    """
    line_items = order.get("line_items", [])
    ordered_ids = [str(item["product_id"]) for item in line_items]
    ordered_titles = [item["title"] for item in line_items]

    candidates = await _fetch_candidates(db, shop_domain, ordered_ids)
    if not candidates:
        return {"offer_id": None, "reason": "no_candidates"}

    # スコアリングして最上位を選択
    best = max(
        candidates,
        key=lambda c: _score(
            float(c["gross_margin"]) / 100,
            int(c["stock_qty"]),
            float(c["accept_rate"]),
        ),
    )

    score = _score(
        float(best["gross_margin"]) / 100,
        int(best["stock_qty"]),
        float(best["accept_rate"]),
    )

    copy_text = await _generate_copy(best["title"], ordered_titles)
    offer_id = str(uuid.uuid4())

    await db.execute(
        """
        INSERT INTO upsell_offers
            (id_str, shop_domain, order_id, product_id, upsell_price, gross_margin, stock_qty, ai_score)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        offer_id,
        shop_domain,
        str(order["id"]),
        best["product_id"],
        float(best["price"]),
        float(best["gross_margin"]),
        int(best["stock_qty"]),
        score,
    )

    return {
        "offer_id": offer_id,
        "product_id": best["product_id"],
        "title": best["title"],
        "price": float(best["price"]),
        "copy": copy_text,
        "score": score,
    }
