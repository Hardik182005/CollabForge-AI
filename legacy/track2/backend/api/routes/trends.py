import sys
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.track02_content.trend_service import TrendService

router = APIRouter()
service = TrendService()


class DiscoverRequest(BaseModel):
    category: str = "all"
    limit: int = 10


@router.post("/discover")
async def discover_trends(request: DiscoverRequest):
    trends = await service.discover_trends(
        category=request.category,
        limit=request.limit,
    )
    is_live = bool(trends and trends[0].get("is_live"))
    return {"status": "success", "trends": trends, "count": len(trends), "is_live": is_live}


@router.get("/categories")
async def get_categories():
    return {
        "status": "success",
        "categories": [
            "Tech",
            "Finance",
            "Marketing",
            "Social",
            "Creator Economy",
            "AI",
        ],
    }


@router.get("/{trend_id}")
async def get_trend_detail(trend_id: str):
    detail = service.get_trend_detail(trend_id)
    if "error" in detail:
        raise HTTPException(status_code=404, detail=detail["error"])
    return {"status": "success", "trend": detail}
