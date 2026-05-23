"""
PostLift AI — Offer Engine
AI が粗利・在庫・承諾率を加味してポスト購入オファーを選定・生成する
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Optional
from openai import AsyncOpenAI

client = AsyncOpenAI()


@dataclass
class Product:
    id: str
    title: str
    price: float
    margin_rate: float
    stock_qty: int
    acceptance_score: float = 0.0


@dataclass
class OfferResult:
    product: Product
    copy: str
    cta: str


class OfferEngine:
    """
    1注文に対して最適なアップセルオファーを1つ選定・生成する
    """

    def __init__(
        self,
        margin_threshold: float = 0.30,
        stock_threshold: int = 5,
    ):
        self.margin_threshold = margin_threshold
        self.stock_threshold = stock_threshold

    def filter_candidates(self, candidates: list[Product]) -> list[Product]:
        """粗利・在庫フィルタ"""
        return [
            p for p in candidates
            if p.margin_rate >= self.margin_threshold
            and p.stock_qty > self.stock_threshold
        ]

    def rank_candidates(self, candidates: list[Product]) -> list[Product]:
        """承諾率スコア降順でソート"""
        return sorted(candidates, key=lambda p: p.acceptance_score, reverse=True)

    async def generate_copy(
        self,
        product: Product,
        purchased_items: list[str],
        lang: str = "ja",
    ) -> tuple[str, str]:
        """LLM でオファーコピーを生成"""
        system_prompt = (
            "You are a conversion copywriter for an e-commerce store. "
            "Generate a short, natural one-click upsell offer message. "
            "Output JSON only: {\"copy\": \"...\", \"cta\": \"...\"}"
        )
        user_prompt = (
            f"Product to upsell: {product.title} (¥{product.price:,.0f})\n"
            f"Buyer just purchased: {', '.join(purchased_items)}\n"
            f"Language: {lang}\n"
            f"Requirements:\n"
            f"- copy: max 35 chars, explain why it pairs well\n"
            f"- cta: max 15 chars, action-oriented\n"
        )
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=100,
        )
        data = json.loads(response.choices[0].message.content)
        return data.get("copy", ""), data.get("cta", "追加する")

    async def get_offer(
        self,
        candidates: list[Product],
        purchased_items: list[str],
    ) -> Optional[OfferResult]:
        """メインメソッド: フィルタ → ランキング → コピー生成"""
        filtered = self.filter_candidates(candidates)
        if not filtered:
            return None

        ranked = self.rank_candidates(filtered)
        top = ranked[0]

        copy, cta = await self.generate_copy(top, purchased_items)
        return OfferResult(product=top, copy=copy, cta=cta)
