"""
Real influencer data via the YouTube Data API v3 (free tier).

Given a company / creator name we:
  1. Resolve the channel as cheaply as possible (``forHandle`` / ``forUsername``
     cost 1 quota unit; ``search`` costs 100 and is used only as a last resort).
  2. Pull real channel statistics (subscribers, total views, video count).
  3. Pull recent uploads via the channel's *uploads* playlist
     (``playlistItems`` + ``videos`` — ~2 units, NO search) and aggregate real
     per-video engagement.

Quota-resilient by design: each analyze costs ~3 quota units instead of ~200,
and if the (optional) recent-video lookup fails — e.g. the daily Search/quota
is exhausted — we STILL return the real channel-level metrics (subscribers,
views) rather than discarding everything. No fabricated follower counts are
ever returned from here; only engagement is approximated when per-video data
is temporarily unavailable.
"""
import sys
import os

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import settings

_BASE = "https://www.googleapis.com/youtube/v3"


def _engagement_rate(views: int, likes: int, comments: int) -> float:
    """Engagement as (likes + comments) / views, expressed as a percentage."""
    if views <= 0:
        return 0.0
    return round((likes + comments) / views * 100, 2)


async def fetch_channel(query: str) -> dict | None:
    """
    Resolve ``query`` (a company / creator name or @handle) to a real YouTube
    channel and return live metrics. Returns ``None`` when unavailable.
    """
    if not settings.YOUTUBE_API_KEY:
        return None

    key = settings.YOUTUBE_API_KEY
    handle = query.strip().lstrip("@")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            info = await _resolve_channel(client, key, handle)
            if not info:
                return None

            snip = info.get("snippet", {})
            stats = info.get("statistics", {})
            content = info.get("contentDetails", {})
            channel_id = info.get("id")

            subscribers = int(stats.get("subscriberCount", 0))
            total_views = int(stats.get("viewCount", 0))
            video_count = int(stats.get("videoCount", 0))

            # Real channel data must have at least subscribers or views.
            if subscribers <= 0 and total_views <= 0:
                return None

            uploads = (content.get("relatedPlaylists") or {}).get("uploads")

            # Recent uploads → real engagement. Non-fatal: if this fails (e.g.
            # quota), we keep the real channel-level metrics below.
            recent = await _recent_video_stats(client, key, uploads, total_views, video_count)

            return {
                "source": "youtube",
                "handle": snip.get("title", handle),
                "channel_id": channel_id,
                "description": snip.get("description", "")[:300],
                "thumbnail": snip.get("thumbnails", {}).get("default", {}).get("url", ""),
                "followers": subscribers,
                "total_views": total_views,
                "video_count": video_count,
                "engagement_rate": recent["engagement_rate"],
                "avg_likes": recent["avg_likes"],
                "avg_comments": recent["avg_comments"],
                "avg_views": recent["avg_views"],
                "post_frequency": recent["post_frequency"],
                "recent_videos": recent["videos"],
            }
    except Exception:
        return None


async def _resolve_channel(client: httpx.AsyncClient, key: str, handle: str) -> dict | None:
    """
    Return a channels.list item (snippet+statistics+contentDetails) for the
    query. Tries the cheap lookups first (1 unit each) and only falls back to
    ``search`` (100 units) when those miss — so a single analyze normally never
    touches the Search Queries quota at all.
    """
    part = "snippet,statistics,contentDetails"

    # 1) Modern @handle lookup (1 unit).
    # 2) Legacy username lookup (1 unit).
    for params in (
        {"part": part, "forHandle": handle, "key": key},
        {"part": part, "forUsername": handle, "key": key},
    ):
        try:
            r = await client.get(f"{_BASE}/channels", params=params)
            if r.status_code == 200:
                items = r.json().get("items", [])
                if items:
                    return items[0]
        except Exception:
            pass

    # 3) Last resort: search (100 units), then re-fetch full channel by id.
    try:
        s = await client.get(
            f"{_BASE}/search",
            params={"part": "snippet", "q": handle, "type": "channel", "maxResults": 1, "key": key},
        )
        if s.status_code == 200:
            items = s.json().get("items", [])
            if items:
                cid = items[0]["snippet"]["channelId"]
                ch = await client.get(f"{_BASE}/channels", params={"part": part, "id": cid, "key": key})
                if ch.status_code == 200:
                    ci = ch.json().get("items", [])
                    if ci:
                        return ci[0]
    except Exception:
        pass

    return None


async def _recent_video_stats(
    client: httpx.AsyncClient, key: str, uploads_playlist: str | None,
    total_views: int, video_count: int,
) -> dict:
    """
    Aggregate engagement across the channel's most recent uploads using the
    uploads playlist (no ``search`` quota). If anything is unavailable, fall
    back to a channel-level estimate derived from REAL totals so scoring stays
    meaningful — never raises.
    """
    # Channel-wide real average view count, used as the resilient fallback.
    fallback_avg_views = (total_views // video_count) if video_count else 0
    fallback = {
        "engagement_rate": _engagement_rate(
            fallback_avg_views, int(fallback_avg_views * 0.04), int(fallback_avg_views * 0.003)
        ),
        "avg_likes": int(fallback_avg_views * 0.04),
        "avg_comments": int(fallback_avg_views * 0.003),
        "avg_views": fallback_avg_views,
        "post_frequency": 1.0,
        "videos": [],
    }

    if not uploads_playlist:
        return fallback

    try:
        pl = await client.get(
            f"{_BASE}/playlistItems",
            params={"part": "contentDetails", "playlistId": uploads_playlist, "maxResults": 10, "key": key},
        )
        pl.raise_for_status()
        video_ids = [
            it["contentDetails"]["videoId"]
            for it in pl.json().get("items", [])
            if it.get("contentDetails", {}).get("videoId")
        ]
        if not video_ids:
            return fallback

        vids = await client.get(
            f"{_BASE}/videos",
            params={"part": "statistics,snippet", "id": ",".join(video_ids), "key": key},
        )
        vids.raise_for_status()
        items = vids.json().get("items", [])
        if not items:
            return fallback

        total_v = total_l = total_c = 0
        videos = []
        dates = []
        for v in items:
            s = v.get("statistics", {})
            views = int(s.get("viewCount", 0))
            likes = int(s.get("likeCount", 0))
            comments = int(s.get("commentCount", 0))
            total_v += views
            total_l += likes
            total_c += comments
            dates.append(v.get("snippet", {}).get("publishedAt", ""))
            videos.append({
                "title": v.get("snippet", {}).get("title", "")[:120],
                "views": views,
                "likes": likes,
                "comments": comments,
                "published_at": v.get("snippet", {}).get("publishedAt", ""),
            })

        n = len(items)
        avg_views = total_v // n
        avg_likes = total_l // n
        avg_comments = total_c // n

        return {
            "engagement_rate": _engagement_rate(avg_views, avg_likes, avg_comments),
            "avg_likes": avg_likes,
            "avg_comments": avg_comments,
            "avg_views": avg_views,
            "post_frequency": _posts_per_week(dates),
            "videos": videos,
        }
    except Exception:
        return fallback


def _posts_per_week(iso_dates: list) -> float:
    """Estimate uploads/week from the spread of recent publish timestamps."""
    from datetime import datetime

    parsed = []
    for d in iso_dates:
        try:
            parsed.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
        except (ValueError, AttributeError):
            continue
    if len(parsed) < 2:
        return 1.0
    span_days = (max(parsed) - min(parsed)).days or 1
    return round(len(parsed) / (span_days / 7.0), 1)
