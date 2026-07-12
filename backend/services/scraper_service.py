"""
Trend scraper: pulls live data from Reddit, NewsAPI, YouTube.
Falls back to curated static data when API keys are missing.
"""
import httpx
import json
import os
import sys
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import settings

# NOTE: fabricated static trends were removed — live sources or nothing.

async def fetch_reddit_trends(category: str = "all", limit: int = 5) -> list:
    # Reddit's public .json listings work WITHOUT API keys as long as we send a
    # descriptive User-Agent. No client_id/secret required.
    subreddits = {
        "AI": "artificial+MachineLearning",
        "Marketing": "marketing+socialmedia",
        "Business": "Entrepreneur+business",
        "Startups": "startups",
        "Finance": "investing+personalfinance",
        "Creator Economy": "NewTubers+content_marketing",
    }
    sub = subreddits.get(category, "technology+marketing+artificial")
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}&raw_json=1"
    headers = {
        "User-Agent": "python:collabforge-ai-trends:v1.0 (by /u/collabforge)",
        "Accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            posts = r.json()["data"]["children"]
            results = []
            for p in posts[:limit]:
                d = p["data"]
                upvotes = int(d.get("score", 0))
                results.append({
                    "title": d.get("title", "")[:100],
                    "category": category if category != "all" else "General",
                    "signal": f"{upvotes:,} upvotes",
                    "signal_value": upvotes,
                    "sources": ["Reddit"],
                    "url": f"https://reddit.com{d.get('permalink', '')}",
                })
            return results
    except Exception:
        return []

async def fetch_newsapi_trends(category: str = "all", limit: int = 5) -> list:
    if not settings.NEWS_API_KEY:
        return []
    queries = {
        "AI": "artificial intelligence creator",
        "Marketing": "influencer marketing 2026",
        "Business": "creator economy startup",
        "Finance": "influencer finance brand",
        "Startups": "startup founder brand",
        "Creator Economy": "content creator monetization",
    }
    q = queries.get(category, "influencer marketing AI content creator")
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": q,
        "sortBy": "popularity",
        "pageSize": limit,
        "language": "en",
        "apiKey": settings.NEWS_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, params=params)
            articles = r.json().get("articles", [])
            results = []
            for a in articles[:limit]:
                results.append({
                    "title": a.get("title", "")[:100],
                    "category": category if category != "all" else "News",
                    "signal": "trending in news (popularity-ranked)",
                    "signal_value": 0,
                    "sources": ["NewsAPI"],
                    "url": a.get("url", ""),
                })
            return results
    except Exception:
        return []

async def fetch_google_news_trends(category: str = "all", limit: int = 5) -> list:
    """Keyless news trends via the public Google News RSS feed (no API key)."""
    import re
    from urllib.parse import quote_plus
    from xml.etree import ElementTree as ET

    queries = {
        "AI": "artificial intelligence content creator",
        "Marketing": "influencer marketing 2026",
        "Business": "creator economy startup",
        "Finance": "creator economy funding",
        "Startups": "startup founder personal brand",
        "Creator Economy": "content creator monetization",
        "Social": "social media algorithm 2026",
    }
    q = queries.get(category, "influencer marketing AI content creator")
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
    )
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CollabForgeAI/1.0)"}
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            r.raise_for_status()
            root = ET.fromstring(r.text)
            items = root.findall(".//item")
            results = []
            for it in items[:limit]:
                title = (it.findtext("title") or "").strip()
                link = (it.findtext("link") or "").strip()
                if not title:
                    continue
                # Google News titles end with " - Source"; trim the source tag.
                clean = re.sub(r"\s+-\s+[^-]+$", "", title)[:100]
                results.append({
                    "title": clean,
                    "category": category if category != "all" else "News",
                    "signal": "current news coverage",
                    "signal_value": 0,
                    "sources": ["Google News"],
                    "url": link,
                })
            return results
    except Exception:
        return []


async def fetch_youtube_trends(category: str = "all", limit: int = 5) -> list:
    """On-theme YouTube trends: search creator/marketing keywords (not generic
    most-popular), then rank by real view counts."""
    if not settings.YOUTUBE_API_KEY:
        return []
    key = settings.YOUTUBE_API_KEY
    queries = {
        "AI": "AI content creation tools",
        "Marketing": "influencer marketing strategy 2026",
        "Business": "creator economy business",
        "Finance": "creator monetization income",
        "Startups": "personal branding founder",
        "Creator Economy": "grow social media audience",
        "Social": "social media algorithm tips",
    }
    q = queries.get(category, "creator economy influencer marketing")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 1) Search relevant videos from the past 3 months, by view count.
            from datetime import datetime, timedelta, timezone
            after = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            s = await client.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet", "q": q, "type": "video",
                    "order": "viewCount", "publishedAfter": after,
                    "relevanceLanguage": "en", "maxResults": limit, "key": key,
                },
            )
            s.raise_for_status()
            ids = [it["id"]["videoId"] for it in s.json().get("items", []) if it.get("id", {}).get("videoId")]
            if not ids:
                return []
            # 2) Fetch real statistics for scoring.
            v = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "snippet,statistics", "id": ",".join(ids), "key": key},
            )
            v.raise_for_status()
            results = []
            for item in v.json().get("items", [])[:limit]:
                snip = item.get("snippet", {})
                views = int(item.get("statistics", {}).get("viewCount", 0))
                results.append({
                    "title": snip.get("title", "")[:100],
                    "category": category if category != "all" else "Creator Economy",
                    "signal": f"{views:,} views in last 90 days",
                    "signal_value": views,
                    "sources": ["YouTube"],
                    "url": f"https://youtube.com/watch?v={item.get('id', '')}",
                })
            return results
    except Exception:
        return []

async def get_live_trends(category: str = "all", limit: int = 10) -> list:
    reddit, news, gnews, youtube = [], [], [], []
    try:
        reddit = await fetch_reddit_trends(category, limit // 2)
    except Exception:
        pass
    try:
        news = await fetch_newsapi_trends(category, limit // 2)
    except Exception:
        pass
    try:
        gnews = await fetch_google_news_trends(category, limit // 2)
    except Exception:
        pass
    try:
        youtube = await fetch_youtube_trends(category, limit // 3)
    except Exception:
        pass

    live = reddit + news + gnews + youtube
    if not live:
        # No invisible static fallback — callers/UI must show an honest
        # "no live trend sources reachable" state.
        return []

    if category.lower() != "all":
        filtered = [t for t in live if t.get("category", "").lower() == category.lower()]
        live = filtered if filtered else live

    seen_titles = set()
    unique = []
    for t in sorted(live, key=lambda x: -(x.get("signal_value") or 0)):
        key = t["title"][:40].lower()
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(t)

    result = []
    for i, t in enumerate(unique[:limit]):
        result.append({
            "rank": i + 1,
            "id": f"trend_{i+1}",
            "title": t["title"],
            "category": t.get("category", "General"),
            "signal": t.get("signal", ""),
            "sources": t.get("sources", ["Web"]),
            "url": t.get("url", ""),
        })
    return result
