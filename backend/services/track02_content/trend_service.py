"""Live Trend Radar.

Sources: Anakin Search (topic queries), keyless Reddit/Google News feeds,
YouTube Data API when configured. No static fallback — when live sources
fail the UI shows an honest empty/error state. Trend cards carry the
observable signal (upvotes, views, coverage), source badges and links;
no invented velocity percentages.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.scraper_service import get_live_trends
from services.anakin.client import anakin_client, AnakinError
from services.anakin.normalizer import from_search


class TrendService:
    async def discover_trends(self, category: str = "all", limit: int = 10, topic: str = "") -> list:
        trends = []

        # Topic-specific research through Anakin Search (cited evidence).
        if topic and anakin_client.available:
            try:
                res = await anakin_client.search(
                    f"What is currently trending about {topic}? Recent developments, "
                    "viral discussions and notable coverage from the last few weeks."
                )
                for i, e in enumerate(from_search(res, "web")[:limit]):
                    trends.append({
                        "rank": len(trends) + 1,
                        "id": f"trend_anakin_{i+1}",
                        "title": e.title,
                        "category": category if category != "all" else "Topic Research",
                        "signal": f"published {e.published_at}" if e.published_at else "recent coverage",
                        "sources": ["Anakin Search"],
                        "url": e.url,
                        "snippet": e.snippet,
                        "published_at": e.published_at,
                        "is_live": True,
                        "data_method": "anakin_search",
                    })
            except AnakinError:
                pass

        # Broad category feeds (Reddit/Google News/YouTube).
        try:
            live = await get_live_trends(category, limit)
        except Exception:
            live = []
        for t in live:
            if len(trends) >= limit:
                break
            trends.append({**t, "is_live": True, "data_method": "public_feed"})

        return trends[:limit]

    def get_trend_detail(self, trend_id: str) -> dict:
        # Details now come inline on each card (url/snippet/signal); there is
        # no static detail store anymore.
        return {"id": trend_id, "error": "Trend not found"}


trend_service = TrendService()
