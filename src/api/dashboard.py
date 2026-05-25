"""
KPI ダッシュボード
GET /dashboard   →  HTML ダッシュボードページを返す
"""
import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, shop_domain: str = "demo.myshopify.com"):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "shop_domain": shop_domain},
    )
