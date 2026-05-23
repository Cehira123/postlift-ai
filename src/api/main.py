"""
PostLift AI — FastAPI Backend
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

app = FastAPI(title="PostLift AI", version="0.1.0")


class OrderItem(BaseModel):
    product_id: str
    title: str
    price: float


class OfferRequest(BaseModel):
    shop_id: str
    order_id: str
    items: List[OrderItem]


class OfferResponse(BaseModel):
    product_id: str
    title: str
    price: float
    copy: str
    cta: str


@app.post("/api/offer", response_model=OfferResponse)
async def get_offer(req: OfferRequest):
    """
    注文情報を受け取り、最適なアップセルオファーを返す
    """
    # TODO: DB から候補商品を取得し OfferEngine を呼び出す
    raise HTTPException(status_code=501, detail="Not implemented yet")


@app.get("/health")
def health():
    return {"status": "ok"}
