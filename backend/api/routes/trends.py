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
    topic: str = ""


@router.post("/discover")
async def discover_trends(request: DiscoverRequest):
    trends = await service.discover_trends(
        category=request.category,
        limit=max(1, min(request.limit, 20)),
        topic=request.topic[:200],
    )
    return {
        "status": "success" if trends else "no_live_sources",
        "trends": trends,
        "count": len(trends),
        "is_live": bool(trends),
        "message": None if trends else "No live trend sources reachable right now — try again shortly.",
    }


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
