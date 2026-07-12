import sys
import os
import json
import hashlib
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.track01_intelligence.ratefluencer_score import RatefluencerScoringEngine
from services.ai_providers.gemini_client import GeminiClient
from services import youtube_service, instagram_service
from services.metrics_resolver import resolve_metrics

router = APIRouter()
engine = RatefluencerScoringEngine()
gemini = GeminiClient()

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "sample_influencers.json",
)


def _load_sample_influencers() -> list:
    try:
        with open(_DATA_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _parse_followers(val) -> int:
    """Convert '2.4M', '780K', 120000, etc. to int."""
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).upper().replace(",", "").strip()
    if s.endswith("M"):
        return int(float(s[:-1]) * 1_000_000)
    if s.endswith("K"):
        return int(float(s[:-1]) * 1_000)
    try:
        return int(float(s))
    except ValueError:
        return 100000


def _parse_percent(val) -> float:
    """Convert '6.8%' or 6.8 to float."""
    if isinstance(val, (int, float)):
        return float(val)
    return float(str(val).replace("%", "").strip())


def _synthetic_metrics(handle: str) -> dict:
    seed = int(hashlib.md5(handle.encode()).hexdigest(), 16)
    followers = 50000 + (seed % 950000)
    engagement_rate = round(2.0 + (seed % 50) / 10.0, 1)
    avg_likes = int(followers * engagement_rate / 100)
    return {
        "handle": handle,
        "followers": followers,
        "engagement_rate": engagement_rate,
        "avg_likes": avg_likes,
        "avg_comments": int(avg_likes * 0.05),
        "post_frequency": round(1.5 + (seed % 7) * 0.5, 1),
        "avg_views": avg_likes * 3,
        "niche": "general",
    }


async def _real_metrics(handle: str, platform: str) -> Optional[dict]:
    """
    Try to pull REAL metrics from a live source based on platform.
    YouTube (free) and Instagram (paid RapidAPI) supported. Returns a metrics
    dict with a 'source' field, or None if no real data is available.
    """
    p = (platform or "").lower()
    data = None
    if p == "instagram":
        data = await instagram_service.fetch_profile(handle)
    elif p == "youtube":
        data = await youtube_service.fetch_channel(handle)
    else:
        # Unknown platform: try YouTube first (free), then Instagram.
        data = await youtube_service.fetch_channel(handle) or await instagram_service.fetch_profile(handle)

    if not data or data.get("followers", 0) <= 0:
        return None

    return {
        "handle": data.get("handle", handle),
        "followers": data["followers"],
        "engagement_rate": data.get("engagement_rate", 0.0),
        "avg_likes": data.get("avg_likes", 0),
        "avg_comments": data.get("avg_comments", 0),
        "post_frequency": data.get("post_frequency", 1.0) or 1.0,
        "avg_views": data.get("avg_views", 0),
        "niche": _infer_niche(data.get("handle", handle)),
        "source": data.get("source", "live"),
        "extra": data,
    }


def _find_influencer(handle: str) -> Optional[dict]:
    data = _load_sample_influencers()
    handle_clean = handle.lower().lstrip("@")
    for inf in data:
        stored = inf.get("handle", "").lower().lstrip("@")
        if handle_clean in stored or stored in handle_clean:
            return inf
    return None


# ── Request Models ────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    handle: str
    platform: str = "instagram"


class GrowthRequest(BaseModel):
    handle: str
    platform: str = "instagram"
    months: int = 12


class AuthenticityRequest(BaseModel):
    handle: str
    platform: str = "instagram"


class BrandsRequest(BaseModel):
    handle: str
    platform: str = "instagram"
    niche: str = "general"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_influencer(request: AnalyzeRequest):
    if not request.handle:
        raise HTTPException(status_code=400, detail="Handle is required")

    # Resolve metrics through the SHARED resolver (live → sample → synthetic)
    # so the dashboard score is identical to the ViraNova agent workstream.
    metrics = await resolve_metrics(request.handle, request.platform)
    niche = metrics["niche"]
    data_source = metrics["data_source"]

    scores = engine.calculate_score(metrics)
    brands = engine.get_brand_matches(niche, scores)
    growth = engine.predict_growth(
        followers=metrics["followers"],
        engagement_rate=metrics["engagement_rate"],
        post_frequency=metrics["post_frequency"],
    )
    authenticity = engine.detect_authenticity(
        followers=metrics["followers"],
        avg_likes=metrics["avg_likes"],
        avg_comments=metrics["avg_comments"],
    )

    summary = await gemini.complete(
        system="You are an expert influencer marketing strategist. Give a 2-sentence strategic assessment.",
        user=(
            f"Influencer: {request.handle}, Ratefluencer Score: {scores['ratefluencer_score']}, "
            f"Niche: {niche}, Followers: {metrics['followers']:,}, "
            f"Platform: {request.platform}, Engagement: {metrics['engagement_rate']}%."
        ),
        max_tokens=200,
    )

    return {
        "status": "success",
        "handle": metrics.get("handle", request.handle),
        "platform": request.platform,
        "niche": niche,
        "data_source": data_source,
        "is_real": metrics.get("is_real", data_source in ("youtube", "instagram", "live")),
        "metrics": {
            "followers": metrics["followers"],
            "engagement_rate": metrics["engagement_rate"],
            "avg_likes": metrics["avg_likes"],
            "avg_comments": metrics["avg_comments"],
            "post_frequency": metrics["post_frequency"],
            "avg_views": metrics["avg_views"],
        },
        "scores": scores,
        "brand_matches": brands,
        "growth": growth,
        "authenticity": authenticity,
        "summary": summary,
    }


@router.post("/growth")
async def predict_growth(request: GrowthRequest):
    if not request.handle:
        raise HTTPException(status_code=400, detail="Handle is required")
    real = await _real_metrics(request.handle, request.platform)
    if real:
        followers, eng, post_freq = real["followers"], real["engagement_rate"], real["post_frequency"]
    else:
        stored = _find_influencer(request.handle)
        if stored:
            details = stored.get("details", {})
            followers = _parse_followers(details.get("followers", 100000))
            eng = _parse_percent(details.get("engagement_rate", 3.0))
            post_freq = _parse_percent(
                str(details.get("post_frequency", "3.0/wk")).split("/")[0]
            )
        else:
            m = _synthetic_metrics(request.handle)
            followers, eng, post_freq = m["followers"], m["engagement_rate"], m["post_frequency"]

    growth = engine.predict_growth(followers, eng, post_freq, months=request.months)
    return {"status": "success", "handle": request.handle, "growth": growth}


@router.post("/authenticity")
async def check_authenticity(request: AuthenticityRequest):
    if not request.handle:
        raise HTTPException(status_code=400, detail="Handle is required")
    real = await _real_metrics(request.handle, request.platform)
    if real:
        followers, avg_likes, avg_comments = real["followers"], real["avg_likes"], real["avg_comments"]
    else:
        stored = _find_influencer(request.handle)
        if stored:
            details = stored.get("details", {})
            followers = _parse_followers(details.get("followers", 100000))
            eng = _parse_percent(details.get("engagement_rate", 3.0))
            avg_likes = int(followers * eng / 100)
            avg_comments = int(avg_likes * 0.05)
        else:
            m = _synthetic_metrics(request.handle)
            followers, avg_likes, avg_comments = m["followers"], m["avg_likes"], m["avg_comments"]

    result = engine.detect_authenticity(followers, avg_likes, avg_comments)
    return {"status": "success", "handle": request.handle, "authenticity": result}


@router.post("/brands")
async def match_brands(request: BrandsRequest):
    if not request.handle:
        raise HTTPException(status_code=400, detail="Handle is required")
    stored = _find_influencer(request.handle)
    niche = request.niche
    if stored:
        niche = _infer_niche(stored.get("handle", request.niche))

    scores = {"ratefluencer_score": 80, "engagement_score": 80}
    brands = engine.get_brand_matches(niche, scores)
    return {"status": "success", "handle": request.handle, "niche": niche, "brands": brands}


def _infer_niche(handle: str) -> str:
    h = handle.lower()
    if any(kw in h for kw in ["fashion", "style", "beauty", "creates", "looks"]):
        return "fashion"
    if any(kw in h for kw in ["tech", "startup", "code", "dev", "ai"]):
        return "tech"
    if any(kw in h for kw in ["wellness", "mindful", "health", "fit", "yoga"]):
        return "wellness"
    return "general"
