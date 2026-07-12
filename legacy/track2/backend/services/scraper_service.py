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

_STATIC_TRENDS = [
    {"title": "AI Agents are replacing social media managers", "category": "AI", "score": 96, "growth_pct": 340, "sources": ["Reddit", "LinkedIn"]},
    {"title": "Short-form video ROI overtakes TV ads", "category": "Marketing", "score": 91, "growth_pct": 220, "sources": ["YouTube", "NewsAPI"]},
    {"title": "Creator economy hits $500B valuation", "category": "Creator Economy", "score": 88, "growth_pct": 185, "sources": ["LinkedIn", "Reddit"]},
    {"title": "Micro-influencers 3x ROI vs mega influencers", "category": "Marketing", "score": 85, "growth_pct": 160, "sources": ["NewsAPI", "LinkedIn"]},
    {"title": "Gemini 2.0 changes content automation forever", "category": "AI", "score": 83, "growth_pct": 140, "sources": ["Reddit", "YouTube"]},
    {"title": "UGC content outperforms brand-produced video", "category": "Marketing", "score": 80, "growth_pct": 120, "sources": ["LinkedIn", "NewsAPI"]},
    {"title": "LinkedIn newsletters overtake email open rates", "category": "Business", "score": 77, "growth_pct": 95, "sources": ["LinkedIn"]},
    {"title": "AI voice cloning for brand content goes mainstream", "category": "AI", "score": 74, "growth_pct": 88, "sources": ["Reddit", "YouTube"]},
    {"title": "Startup founder personal brands drive B2B sales", "category": "Startups", "score": 71, "growth_pct": 75, "sources": ["LinkedIn", "NewsAPI"]},
    {"title": "DeFi influencer marketing compliance crackdown", "category": "Finance", "score": 68, "growth_pct": 60, "sources": ["Reddit", "NewsAPI"]},
]

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
        "User-Agent": "python:creatrix-ai-trends:v2.0 (by /u/creatrixai)",
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
                score = min(100, int(d.get("score", 0) / 50))
                results.append({
                    "title": d.get("title", "")[:100],
                    "category": category if category != "all" else "General",
                    "score": max(50, score),
                    "growth_pct": max(50, score * 2),
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
                seed = int(hashlib.md5(a.get("title", "x").encode()).hexdigest(), 16)
                results.append({
                    "title": a.get("title", "")[:100],
                    "category": category if category != "all" else "News",
                    "score": 60 + (seed % 35),
                    "growth_pct": 50 + (seed % 150),
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
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CreatrixAI/2.0)"}
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
                seed = int(hashlib.md5(title.encode()).hexdigest(), 16)
                results.append({
                    "title": clean,
                    "category": category if category != "all" else "News",
                    "score": 62 + (seed % 33),
                    "growth_pct": 55 + (seed % 140),
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
                score = min(100, int(views / 100000))
                results.append({
                    "title": snip.get("title", "")[:100],
                    "category": category if category != "all" else "Creator Economy",
                    "score": max(55, score),
                    "growth_pct": max(60, score * 3),
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
        live = _STATIC_TRENDS

    if category.lower() != "all":
        filtered = [t for t in live if t.get("category", "").lower() == category.lower()]
        live = filtered if filtered else live

    seen_titles = set()
    unique = []
    for t in sorted(live, key=lambda x: -x.get("score", 0)):
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
            "score": t.get("score", 70),
            "growth_pct": t.get("growth_pct", 100),
            "sources": t.get("sources", ["Web"]),
            "velocity": "rising" if t.get("growth_pct", 0) > 100 else "stable",
            "engagement_potential": "high" if t.get("score", 0) > 80 else "medium",
        })
    return result
