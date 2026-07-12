import sys
import os
import json
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.gemini_client import GeminiClient
from services.scraper_service import get_live_trends

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "sample_trends.json",
)


def _load_sample_trends() -> list:
    try:
        with open(_DATA_PATH, "r") as f:
            raw = json.load(f)
        # Normalise: add id field if missing
        result = []
        for i, t in enumerate(raw):
            trend = dict(t)
            trend.setdefault("id", f"trend_{i+1}")
            trend.setdefault("category", "General")
            result.append(trend)
        return result
    except Exception:
        return [
            {"id": "trend_1", "title": "AI replacing Content Creators", "category": "Tech", "score": 94, "growth_velocity": "+340%", "sources": ["Reddit", "LinkedIn", "YouTube"]},
            {"id": "trend_2", "title": "Micro-influencer ROI study", "category": "Marketing", "score": 88, "growth_velocity": "+185%", "sources": ["Twitter", "NewsAPI"]},
            {"id": "trend_3", "title": "Reels vs TikTok 2026", "category": "Social", "score": 81, "growth_velocity": "+120%", "sources": ["Instagram", "TikTok"]},
            {"id": "trend_4", "title": "Creator economy funding news", "category": "Finance", "score": 77, "growth_velocity": "+95%", "sources": ["NewsAPI", "Crunchbase"]},
            {"id": "trend_5", "title": "Brand UGC strategy shift", "category": "Marketing", "score": 73, "growth_velocity": "+60%", "sources": ["LinkedIn", "Twitter"]},
        ]


_VIRAL_ANGLES = {
    "tech": "AI is eating every industry — and content creation is next. Here's the data.",
    "marketing": "The brands winning in 2026 changed one thing about their influencer strategy.",
    "social": "The algorithm update nobody is talking about — and how to use it.",
    "finance": "The capital is moving. Here's where smart creators are investing their energy.",
    "general": "This trend is flying under the radar — which means huge opportunity right now.",
}

_HOOKS = {
    "tech": "POV: You discover AI before your competitors do...",
    "marketing": "What if I told you the biggest ROI shift in marketing is hiding in plain sight?",
    "social": "Stop using the old playbook. This is what the algorithm rewards now.",
    "finance": "The creator economy just got a serious upgrade. Here's how to ride it.",
    "general": "This trend is going from 0 to 10M views per week. Here's why.",
}


class TrendService:
    def __init__(self):
        self.gemini = GeminiClient()

    async def discover_trends(self, category: str = "all", limit: int = 10) -> list:
        # 1) Try LIVE trends (Reddit + Google News, keyless; YouTube + NewsAPI
        #    when keys present). Fall back to curated static data if nothing.
        live = []
        try:
            live = await get_live_trends(category, limit)
        except Exception:
            live = []

        self.is_live = bool(live)
        raw = live if live else _load_sample_trends()

        if not live and category.lower() != "all":
            filtered = [t for t in raw if t.get("category", "").lower() == category.lower()]
            raw = filtered if filtered else raw

        filtered = raw[:limit]

        enriched = []
        for i, trend in enumerate(filtered):
            cat_key = trend.get("category", "general").lower()
            trend_title = trend.get("trend") or trend.get("title", "")

            # Live items carry growth_pct (int); static carry growth_velocity (str).
            if "growth_velocity" in trend:
                growth_velocity = trend["growth_velocity"]
            else:
                growth_velocity = f"+{trend.get('growth_pct', 100)}%"

            viral_angle = _VIRAL_ANGLES.get(cat_key, _VIRAL_ANGLES["general"])
            script_hook = _HOOKS.get(cat_key, _HOOKS["general"])
            content_idea = f"Short-form reel exploring: {trend_title}"

            enriched_trend = {
                "id": trend.get("id", f"trend_{i+1}"),
                "title": trend_title,
                "category": trend.get("category", "General"),
                "score": trend.get("score", 75),
                "growth_velocity": growth_velocity,
                "sources": trend.get("sources", ["Web"]),
                "url": trend.get("url", ""),
                "viral_angle": viral_angle,
                "script_hook": script_hook,
                "content_idea": content_idea,
                "is_live": bool(live),
            }
            enriched.append(enriched_trend)

        return enriched

    def get_trend_detail(self, trend_id: str) -> dict:
        raw = _load_sample_trends()
        for i, trend in enumerate(raw):
            tid = trend.get("id", f"trend_{i+1}")
            if tid == trend_id:
                trend_title = trend.get("trend") or trend.get("title", "")
                cat_key = trend.get("category", "general").lower()
                return {
                    "id": tid,
                    "title": trend_title,
                    "category": trend.get("category", "General"),
                    "score": trend.get("score", 75),
                    "growth_velocity": trend.get("growth_velocity", "+100%"),
                    "sources": trend.get("sources", []),
                    "viral_angle": _VIRAL_ANGLES.get(cat_key, _VIRAL_ANGLES["general"]),
                    "script_hook": _HOOKS.get(cat_key, _HOOKS["general"]),
                    "content_ideas": [
                        f"Reel: {trend_title} — explained in 30 seconds",
                        f"LinkedIn post: What {trend_title} means for brands in 2026",
                        f"Carousel: 5 ways {trend_title} changes the creator game",
                    ],
                    "brand_opportunities": [
                        "Native sponsor integration",
                        "Co-created content series",
                        "Limited-time campaign activation",
                    ],
                }
        return {"id": trend_id, "error": "Trend not found"}


trend_service = TrendService()
