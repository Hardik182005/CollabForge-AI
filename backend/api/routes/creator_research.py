import sys, os
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.security import research_limiter
from services.research.dossier import build_dossier
from services.research.creator_resolver import resolve_creator
from services.research.reputation_analyzer import analyze_reputation
from services.research.sponsor_detector import detect_sponsors
from services.scoring.rate_estimator import estimate_rate
from services.anakin.client import AnakinError

router = APIRouter()


class CampaignContext(BaseModel):
    product: str = Field("", max_length=300)
    industry: str = Field("", max_length=100)
    goal: str = Field("", max_length=300)
    audience: str = Field("", max_length=300)
    budget: Optional[float] = Field(None, ge=0)
    deliverable: str = Field("integrated_segment", max_length=50)


class ResearchRequest(BaseModel):
    creator: str = Field(..., min_length=1, max_length=120, examples=["Technical Guruji"])
    campaign: Optional[CampaignContext] = None
    include_reputation: bool = True
    include_sponsors: bool = True


class DiscoverRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=200, examples=["hindi tech reviews"])
    platform: str = Field("youtube", max_length=30)
    limit: int = Field(5, ge=1, le=8)


class NameOnlyRequest(BaseModel):
    creator: str = Field(..., min_length=1, max_length=120)


class RateEstimateRequest(BaseModel):
    creator: str = Field(..., min_length=1, max_length=120)
    deliverable: str = Field("integrated_segment", max_length=50)
    usage_rights: bool = False
    exclusivity: bool = False


@router.post("/research")
async def creator_research(req: ResearchRequest, request: Request):
    """Full evidence-backed creator dossier: overview, recent content, themes,
    engagement signals, public sentiment, visible sponsor history, explainable
    fit score, and estimated collaboration range."""
    research_limiter.check(request)
    try:
        return await build_dossier(
            req.creator,
            req.campaign.model_dump() if req.campaign else None,
            include_reputation=req.include_reputation,
            include_sponsors=req.include_sponsors,
        )
    except AnakinError as e:
        raise HTTPException(status_code=e.status if e.status >= 400 else 502, detail=e.to_dict())


@router.post("/discover")
async def creator_discover(req: DiscoverRequest, request: Request):
    """Discover public creators for a topic. YouTube only (the one platform with
    verified live sources); other platforms are disabled in capabilities."""
    research_limiter.check(request)
    if req.platform.lower() not in ("youtube", "any"):
        raise HTTPException(status_code=400, detail=f"Platform '{req.platform}' has no reliable configured source — see /api/v1/system/capabilities")
    from services.anakin.client import anakin_client
    try:
        res = await anakin_client.search(
            f"List up to {req.limit} popular YouTube creators focused on {req.topic}. "
            "For each: channel name, approximate subscribers, and what they cover."
        )
    except AnakinError as e:
        raise HTTPException(status_code=502, detail=e.to_dict())
    from services.anakin.normalizer import from_search
    evidence = from_search(res, "web")
    return {
        "status": "ok",
        "note": "Names discovered via Anakin Search — run /research on a name for verified live data.",
        "results": [e.model_dump() for e in evidence[: req.limit * 2]],
    }


@router.post("/reputation")
async def creator_reputation(req: NameOnlyRequest, request: Request):
    research_limiter.check(request)
    return await analyze_reputation(req.creator)


@router.post("/sponsor-history")
async def creator_sponsor_history(req: NameOnlyRequest, request: Request):
    research_limiter.check(request)
    resolved = await resolve_creator(req.creator)
    videos = resolved["videos"] if resolved else []
    return await detect_sponsors(req.creator, videos)


@router.post("/rate-estimate")
async def creator_rate_estimate(req: RateEstimateRequest, request: Request):
    research_limiter.check(request)
    resolved = await resolve_creator(req.creator)
    if not resolved:
        raise HTTPException(status_code=404, detail="Creator not found in public sources")
    views = [v.get("views") or 0 for v in resolved["videos"] if (v.get("views") or 0) > 0]
    avg_views = int(sum(views) / len(views)) if views else None
    return estimate_rate(avg_views, req.deliverable, usage_rights=req.usage_rights, exclusivity=req.exclusivity)
