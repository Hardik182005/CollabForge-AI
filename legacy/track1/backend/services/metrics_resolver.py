"""Single source of truth for resolving a creator's metrics from a handle.

Both the `/influencer/analyze` dashboard endpoint and the ViraNova agent
workstream call `resolve_metrics`, so the Ratefluencer Score is IDENTICAL no
matter which surface computes it. Resolution order:

    1. live API   — real YouTube (free) / Instagram (paid) data
    2. sample data — curated data/sample_influencers.json
    3. synthetic   — deterministic hash-based fallback (always succeeds)

Every branch returns the same dict shape so callers never special-case it.
"""
import os
import json
import hashlib
from typing import Optional

from . import youtube_service, instagram_service

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # backend/
    "data",
    "sample_influencers.json",
)


def _load_sample_influencers() -> list:
    try:
        with open(_DATA_PATH, "r", encoding="utf-8") as f:
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


def infer_niche(handle: str) -> str:
    h = handle.lower()
    if any(kw in h for kw in ["fashion", "style", "beauty", "creates", "looks"]):
        return "fashion"
    if any(kw in h for kw in ["tech", "startup", "code", "dev", "ai"]):
        return "tech"
    if any(kw in h for kw in ["wellness", "mindful", "health", "fit", "yoga"]):
        return "wellness"
    return "general"


def _find_influencer(handle: str) -> Optional[dict]:
    data = _load_sample_influencers()
    handle_clean = handle.lower().lstrip("@")
    for inf in data:
        stored = inf.get("handle", "").lower().lstrip("@")
        if handle_clean in stored or stored in handle_clean:
            return inf
    return None


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
        "data_source": "estimated",
        "is_real": False,
    }


async def _live_metrics(handle: str, platform: str) -> Optional[dict]:
    """Pull REAL metrics from a live source. Returns None if unavailable."""
    p = (platform or "").lower()
    data = None
    try:
        if p == "instagram":
            data = await instagram_service.fetch_profile(handle)
        elif p == "youtube":
            data = await youtube_service.fetch_channel(handle)
        else:
            # Unknown platform: try YouTube first (free), then Instagram.
            data = await youtube_service.fetch_channel(handle) or await instagram_service.fetch_profile(handle)
    except Exception:
        data = None

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
        "niche": infer_niche(data.get("handle", handle)),
        "data_source": data.get("source", "live"),
        "is_real": True,
        "extra": data,
    }


async def resolve_metrics(handle: str, platform: str) -> dict:
    """Resolve canonical metrics for a handle. ALWAYS returns a dict with:
    handle, followers, engagement_rate, avg_likes, avg_comments,
    post_frequency, avg_views, niche, data_source, is_real.

    This is the ONE function the dashboard and the agent share, so the same
    handle+platform always yields the same Ratefluencer Score on both.
    """
    live = await _live_metrics(handle, platform)
    if live:
        return live

    stored = _find_influencer(handle)
    if stored:
        details = stored.get("details", {})
        followers = _parse_followers(details.get("followers", 100000))
        eng = _parse_percent(details.get("engagement_rate", 3.0))
        avg_views = _parse_followers(details.get("avg_views", 25000))
        post_freq = _parse_percent(
            str(details.get("post_frequency", "3.0/wk")).split("/")[0]
        )
        avg_likes = int(followers * eng / 100)
        return {
            "handle": handle,
            "followers": followers,
            "engagement_rate": eng,
            "avg_likes": avg_likes,
            "avg_comments": int(avg_likes * 0.05),
            "post_frequency": post_freq,
            "avg_views": avg_views,
            "niche": infer_niche(stored.get("handle", "")),
            "data_source": "sample",
            "is_real": False,
        }

    return _synthetic_metrics(handle)
