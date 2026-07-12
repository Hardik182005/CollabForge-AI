"""Runtime capability registry.

Probes what is actually usable right now and caches the answer. The frontend
loads GET /api/v1/system/capabilities and renders only enabled features —
no clickable feature may return fake output.
"""
import asyncio
import json
import os
import time
from typing import Optional

from .client import anakin_client, AnakinError

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import settings

_ACTIONS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "anakin_actions.json",
)

_PROBE_TTL = 600  # re-probe Wire every 10 minutes
_state = {"probed_at": 0.0, "wire_live": None}
_probe_lock = asyncio.Lock()


def verified_actions() -> dict:
    """Verified Wire action registry (generated from the live catalog — never invented)."""
    try:
        with open(_ACTIONS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"catalogs": {}}


def has_action(catalog: str, action_id: str) -> bool:
    return any(
        a["action_id"] == action_id
        for a in verified_actions().get("catalogs", {}).get(catalog, [])
    )


async def wire_is_live(force: bool = False) -> bool:
    """Cheap live probe: execute the lowest-cost Wire action and see whether
    execution (not just submission) succeeds. Cached for _PROBE_TTL."""
    if not anakin_client.available:
        return False
    async with _probe_lock:
        if not force and _state["wire_live"] is not None and time.monotonic() - _state["probed_at"] < _PROBE_TTL:
            return _state["wire_live"]
        live = False
        try:
            job = await anakin_client.wire_task(
                "gt_suggestions", {"keyword": "technology"}, cache=False,
            )
            live = bool(job)
        except AnakinError:
            live = False
        _state.update(probed_at=time.monotonic(), wire_live=live)
        return live


def _verified_action_count() -> int:
    cats = verified_actions().get("catalogs", {})
    return sum(len(v) for v in cats.values())


def _ffmpeg_available() -> bool:
    import shutil
    return bool(shutil.which("ffmpeg"))


async def capabilities() -> dict:
    anakin_ok = anakin_client.available
    wire = await wire_is_live() if anakin_ok else False
    llm = bool(settings.OPENAI_API_KEY or settings.GROQ_API_KEY or settings.GEMINI_API_KEY)

    def src(enabled: bool, method: str = "", confidence: str = "live", reason: str = ""):
        d: dict = {"enabled": enabled}
        if enabled:
            d["method"] = method
            d["confidence"] = confidence
        elif reason:
            d["reason"] = reason
        return d

    yt_method = "wire" if wire else "anakin_scrape"

    def prov(ok: bool, reason: str = "", **extra) -> dict:
        d: dict = {"available": ok, **extra}
        if not ok and reason:
            d["reason"] = reason
        return d

    return {
        # ── spec §10 provider blocks (frontend derives availability from these) ──
        "anakin": {
            "available": anakin_ok,
            "wire": {"available": wire, "verifiedActions": _verified_action_count(),
                     **({} if wire else {"reason": "Wire execution unavailable upstream — degraded to Scraper/Search"})},
            "scraper": {"available": anakin_ok},
            "search": {"available": anakin_ok},
        },
        "openai": prov(bool(settings.OPENAI_API_KEY), "API key not configured"),
        "elevenlabs": prov(bool(settings.ELEVENLABS_API_KEY), "API key not configured"),
        "youtube_api": prov(bool(settings.YOUTUBE_API_KEY), "API key not configured (Anakin covers YouTube)"),
        "s3": prov(bool(settings.AWS_S3_BUCKET), "AWS_S3_BUCKET not configured"),
        "dynamodb": prov(settings.DATABASE_MODE == "dynamodb" and bool(settings.AWS_DYNAMODB_TABLE),
                         "Using local persistence (DATABASE_MODE != dynamodb)"),
        "ffmpeg": prov(_ffmpeg_available(), "ffmpeg not found on PATH"),
        # ── richer gating retained for the app shell ──
        "sources": {
            "youtube": src(anakin_ok, yt_method),
            "reddit": src(anakin_ok, "wire" if wire else "anakin_search"),
            "google_news": src(anakin_ok, "wire" if wire else "anakin_search"),
            "google_trends": src(wire, "wire") if wire else src(False, reason="Wire execution currently unavailable"),
            "web": src(anakin_ok, "anakin_search"),
            "business_website": src(anakin_ok, "anakin_scrape"),
            "instagram": src(False, reason="No authenticated or reliable source configured"),
            "tiktok": src(False, reason="No authenticated or reliable source configured"),
            "x_twitter": src(False, reason="No authenticated or reliable source configured"),
        },
        "features": {
            "business_dna": src(anakin_ok and llm, "anakin_scrape+llm"),
            "creator_research": src(anakin_ok and llm, f"{yt_method}+anakin_search+llm"),
            "creator_compare": src(anakin_ok and llm, "derived"),
            "trend_radar": src(anakin_ok, "anakin_search+public_feeds"),
            "outreach_writer": src(llm, "llm_over_evidence"),
            "contract_builder": src(llm, "llm_template"),
            "campaign_brief": src(llm, "llm_over_evidence"),
            "roi_scenario": src(True, "editable_assumptions", "estimated"),
            "voice_studio": src(bool(settings.ELEVENLABS_API_KEY), "elevenlabs"),
            "image_generation": src(bool(settings.OPENAI_API_KEY), "openai_images"),
            "autopilot": src(anakin_ok and llm, "workflow"),
            "email_sending": src(False, reason="No Wire email/write action available — drafts only"),
        },
    }
