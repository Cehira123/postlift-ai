"""
顧客履歴スコアリング — RFM 分析
Shopify Admin API から顧客の注文履歴を取得し、
Recency・Frequency・Monetary スコアを計算してDBに保存する。
オファーエンジンはこのスコアを使ってターゲティング精度を上げる。
"""
from __future__ import annotations

import os
from datetime import datetime, timezone

import httpx

SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")


async def fetch_customer_orders(
    shop: str, access_token: str, customer_id: str
) -> list[dict]:
    """Shopify Admin API から顧客の注文履歴を取得する"""
    url = (
        f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}"
        f"/orders.json?customer_id={customer_id}&status=any&limit=250"
        f"&fields=id,total_price,created_at"
    )
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            url,
            headers={"X-Shopify-Access-Token": access_token},
        )
        resp.raise_for_status()
        return resp.json().get("orders", [])


def _calc_rfm(orders: list[dict]) -> dict:
    """
    RFM スコア計算。
    - Recency : 最終注文からの経過日数（少ないほど良い → 0〜1 で正規化後反転）
    - Frequency: 注文回数（正規化閾値=20）
    - Monetary : 総購入額（正規化閾値=200,000円）
    戻り値: {recency_days, frequency, monetary, rfm_score}
    """
    if not orders:
        return {"recency_days": None, "frequency": 0, "monetary": 0.0, "rfm_score": 0.0}

    now = datetime.now(timezone.utc)
    dates = []
    total = 0.0

    for o in orders:
        raw = o.get("created_at", "")
        if raw:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                dates.append(dt)
            except ValueError:
                pass
        total += float(o.get("total_price", 0))

    frequency = len(dates)
    recency_days = int((now - max(dates)).days) if dates else 9999
    monetary = total

    # 正規化（0〜1 に）
    r_norm = max(0.0, 1.0 - recency_days / 365.0)  # 365日で 0 に
    f_norm = min(frequency / 20.0, 1.0)             # 20件で max
    m_norm = min(monetary / 200_000.0, 1.0)          # 20万円で max

    rfm_score = round(0.3 * r_norm + 0.3 * f_norm + 0.4 * m_norm, 4)

    return {
        "recency_days": recency_days,
        "frequency": frequency,
        "monetary": round(monetary, 2),
        "rfm_score": rfm_score,
    }


async def upsert_customer_score(
    db,
    shop_domain: str,
    access_token: str,
    customer_id: str,
) -> dict:
    """顧客スコアを計算してDBに upsert する"""
    try:
        orders = await fetch_customer_orders(shop_domain, access_token, customer_id)
        rfm = _calc_rfm(orders)
    except Exception:
        rfm = {"recency_days": None, "frequency": 0, "monetary": 0.0, "rfm_score": 0.0}

    await db.execute(
        """
        INSERT INTO customer_scores
            (shop_domain, customer_id, recency_days, frequency, monetary, rfm_score, updated_at)
        VALUES ($1, $2, $3, $4, $5, $6, NOW())
        ON CONFLICT (shop_domain, customer_id) DO UPDATE SET
            recency_days = EXCLUDED.recency_days,
            frequency    = EXCLUDED.frequency,
            monetary     = EXCLUDED.monetary,
            rfm_score    = EXCLUDED.rfm_score,
            updated_at   = NOW()
        """,
        shop_domain, customer_id,
        rfm["recency_days"], rfm["frequency"],
        rfm["monetary"], rfm["rfm_score"],
    )
    return rfm


async def get_customer_score(db, shop_domain: str, customer_id: str) -> float:
    """DB から顧客スコアを取得する（なければ 0.5 をデフォルト）"""
    row = await db.fetchrow(
        "SELECT rfm_score FROM customer_scores WHERE shop_domain=$1 AND customer_id=$2",
        shop_domain, customer_id,
    )
    return float(row["rfm_score"]) if row else 0.5
