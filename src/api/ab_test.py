"""
A/B テストフレームワーク
- オファー生成時にバリアント（A/B）をランダムに割り当て
- 統計的有意差（カイ二乗検定）を計算して勝者を判定
POST /ab-tests/record         → バリアント記録
POST /ab-tests/convert        → コンバージョン記録
GET  /ab-tests/results        → 実験結果・有意差
"""
import math
import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.db.session import get_db_dep

router = APIRouter(prefix="/ab-tests", tags=["ab-tests"])


def _chi2_pvalue(a_converted: int, a_total: int, b_converted: int, b_total: int) -> float:
    """
    2×2 カイ二乗検定で p 値を近似計算する。
    外部ライブラリ不要の純 Python 実装。
    """
    if a_total == 0 or b_total == 0:
        return 1.0

    n = a_total + b_total
    a_not = a_total - a_converted
    b_not = b_total - b_converted
    total_conv = a_converted + b_converted
    total_not = a_not + b_not

    if total_conv == 0 or total_not == 0:
        return 1.0

    # Expected values
    e_ac = a_total * total_conv / n
    e_an = a_total * total_not / n
    e_bc = b_total * total_conv / n
    e_bn = b_total * total_not / n

    if any(e == 0 for e in [e_ac, e_an, e_bc, e_bn]):
        return 1.0

    chi2 = (
        (a_converted - e_ac) ** 2 / e_ac
        + (a_not - e_an) ** 2 / e_an
        + (b_converted - e_bc) ** 2 / e_bc
        + (b_not - e_bn) ** 2 / e_bn
    )
    # df=1 の chi2 CDF 近似（Wilson-Hilferty変換）
    x = chi2
    k = 1
    z = ((x / k) ** (1 / 3) - (1 - 2 / (9 * k))) / math.sqrt(2 / (9 * k))
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return max(0.0, min(1.0, p))


def assign_variant() -> str:
    """50/50 でバリアントを割り当てる"""
    return "A" if random.random() < 0.5 else "B"


class RecordRequest(BaseModel):
    shop_domain: str
    experiment_name: str
    variant: str
    offer_id: Optional[str] = None


class ConvertRequest(BaseModel):
    offer_id: str
    converted: bool


@router.post("/record")
async def record_experiment(body: RecordRequest, db=Depends(get_db_dep)):
    """バリアント割り当てを記録する"""
    if body.variant not in ("A", "B"):
        raise HTTPException(status_code=422, detail="variant must be A or B")

    row = await db.fetchrow(
        """
        INSERT INTO ab_experiments (shop_domain, experiment_name, variant, offer_id)
        VALUES ($1, $2, $3, $4)
        RETURNING id
        """,
        body.shop_domain, body.experiment_name, body.variant, body.offer_id,
    )
    return {"id": row["id"], "variant": body.variant}


@router.post("/convert")
async def record_conversion(body: ConvertRequest, db=Depends(get_db_dep)):
    """コンバージョン（承諾/拒否）を記録する"""
    result = await db.execute(
        """
        UPDATE ab_experiments SET converted = $1
        WHERE offer_id = $2 AND converted IS NULL
        """,
        body.converted, body.offer_id,
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="experiment record not found")
    return {"offer_id": body.offer_id, "converted": body.converted}


@router.get("/results")
async def get_results(
    shop_domain: str = Query(...),
    experiment_name: str = Query(...),
    db=Depends(get_db_dep),
):
    """
    実験結果を返す。p値 < 0.05 で統計的有意差あり。
    """
    rows = await db.fetch(
        """
        SELECT
            variant,
            COUNT(*)                                   AS total,
            SUM(CASE WHEN converted THEN 1 ELSE 0 END) AS conversions
        FROM ab_experiments
        WHERE shop_domain = $1 AND experiment_name = $2
        GROUP BY variant
        """,
        shop_domain, experiment_name,
    )

    stats: dict = {}
    for r in rows:
        v = r["variant"]
        total = int(r["total"])
        conv = int(r["conversions"])
        rate = round(conv / total * 100, 2) if total else 0
        stats[v] = {"total": total, "conversions": conv, "rate_pct": rate}

    a = stats.get("A", {"total": 0, "conversions": 0, "rate_pct": 0})
    b = stats.get("B", {"total": 0, "conversions": 0, "rate_pct": 0})

    p_value = _chi2_pvalue(
        a["conversions"], a["total"],
        b["conversions"], b["total"],
    )
    significant = p_value < 0.05
    winner = None
    if significant:
        winner = "A" if a["rate_pct"] >= b["rate_pct"] else "B"

    return {
        "experiment_name": experiment_name,
        "A": a,
        "B": b,
        "p_value": round(p_value, 4),
        "significant": significant,
        "winner": winner,
        "message": (
            f"バリアント{winner}が統計的有意に優れています (p={p_value:.4f})"
            if winner else
            f"まだ有意差なし (p={p_value:.4f}, サンプル不足の可能性あり)"
        ),
    }
