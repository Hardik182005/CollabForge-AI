"""Creator research dossier orchestrator.

Runs resolver → content intelligence → themes → engagement signals →
reputation → sponsor history → fit score → rate estimate, tolerating
partial source failure. Every fact is backed by evidence; missing data
lowers confidence and is listed, never fabricated.
"""
import asyncio
import json
import re
import statistics

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.research.creator_resolver import resolve_creator
from services.research.reputation_analyzer import analyze_reputation
from services.research.sponsor_detector import detect_sponsors
from services.scoring.creator_fit import compute_fit
from services.scoring.rate_estimator import estimate_rate
from services.ai_providers.openai_client import OpenAIChatClient
from models.evidence import Evidence, dedupe_evidence


async def build_dossier(
    creator_query: str,
    campaign_context: dict | None = None,
    include_reputation: bool = True,
    include_sponsors: bool = True,
) -> dict:
    campaign_context = campaign_context or {}
    resolved = await resolve_creator(creator_query)
    if not resolved:
        return {
            "status": "not_found",
            "message": (
                f"Could not resolve '{creator_query}' to a public YouTube channel. "
                "Check spelling, or the creator may not have enough public presence."
            ),
        }

    channel = resolved["channel"]
    videos = resolved["videos"]
    evidence: list = list(resolved["evidence"])
    for v in videos[:12]:
        evidence.append(Evidence(
            source="youtube", source_type="video", title=v.get("title", "")[:150],
            url=v.get("url", ""), published_at=v.get("published") or None,
            metrics={"views": v.get("views")},
            data_method=resolved["data_method"], confidence="high",
        ))

    partial_failures = []
    reputation = sponsors = None
    themes_task = _analyze_themes(channel, videos, campaign_context)
    tasks = [themes_task]
    if include_reputation:
        tasks.append(analyze_reputation(channel["name"]))
    if include_sponsors:
        tasks.append(detect_sponsors(channel["name"], videos))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    themes = results[0] if not isinstance(results[0], Exception) else {}
    if isinstance(results[0], Exception):
        partial_failures.append({"section": "themes", "error": str(results[0])[:200]})
    idx = 1
    if include_reputation:
        reputation = results[idx] if not isinstance(results[idx], Exception) else None
        if reputation is None:
            partial_failures.append({"section": "reputation", "error": str(results[idx])[:200]})
        idx += 1
    if include_sponsors:
        sponsors = results[idx] if not isinstance(results[idx], Exception) else None
        if sponsors is None:
            partial_failures.append({"section": "sponsors", "error": str(results[idx])[:200]})

    engagement = _engagement_signals(channel, videos)

    # ── Fit score components ────────────────────────────────────────────
    relevance = themes.get("relevance_score") if isinstance(themes, dict) else None
    brand_safety = _brand_safety_from_reputation(reputation)
    sponsor_compat = _sponsor_compat(sponsors, campaign_context)
    budget_fit, rate = _budget_fit(engagement, campaign_context)

    fit = compute_fit(
        relevance=relevance,
        engagement_inputs={"subscribers": channel.get("subscribers"), "avg_views": engagement.get("avg_views")},
        videos=videos,
        brand_safety=brand_safety,
        sponsor_compatibility=sponsor_compat,
        budget_fit=budget_fit,
    )
    fit["strengths"] = [c["name"] for c in fit.get("components", []) if c["score"] >= 70]
    fit["risks"] = [c["name"] for c in fit.get("components", []) if c["score"] < 45]

    if reputation and reputation.get("evidence"):
        evidence.extend(Evidence(**e) for e in reputation["evidence"] if isinstance(e, dict))

    return {
        "status": "ok",
        "query": creator_query,
        "overview": {
            **channel,
            "posting_frequency_note": engagement.get("posting_note", "unknown"),
            "content_pillars": themes.get("content_pillars", []) if isinstance(themes, dict) else [],
            "niche": themes.get("niche", "") if isinstance(themes, dict) else "",
        },
        "recent_content": videos,
        "themes": themes if isinstance(themes, dict) else {},
        "engagement_signals": engagement,
        "reputation": reputation,
        "sponsor_history": sponsors,
        "fit_score": fit,
        "rate_estimate": rate,
        "partial_failures": partial_failures,
        "data_method": resolved["data_method"],
        "evidence": [e.model_dump() for e in dedupe_evidence(evidence)[:40]],
    }


def _engagement_signals(channel: dict, videos: list) -> dict:
    views = [v.get("views") or 0 for v in videos if (v.get("views") or 0) > 0]
    subs = channel.get("subscribers") or 0
    out: dict = {"videos_with_view_data": len(views), "missing_data": []}
    if views:
        out["avg_views"] = int(sum(views) / len(views))
        out["median_views"] = int(statistics.median(views))
        out["top_video_views"] = max(views)
        out["low_video_views"] = min(views)
        if subs:
            out["views_to_subscribers_ratio"] = round(out["avg_views"] / subs, 4)
        mean = out["avg_views"]
        if len(views) >= 4 and mean:
            cv = (statistics.pstdev(views)) / mean
            out["view_consistency"] = "high" if cv < 0.5 else "medium" if cv < 1.0 else "low"
        outliers = [v for v in videos if (v.get("views") or 0) > 2.5 * (out["median_views"] or 1)]
        out["outlier_posts"] = [{"title": o.get("title"), "views": o.get("views"), "url": o.get("url")} for o in outliers[:3]]
    else:
        out["missing_data"].append("per-video view counts unavailable from current sources")
    if not subs:
        out["missing_data"].append("subscriber count unavailable")
    published = [v.get("published") for v in videos if v.get("published")]
    out["posting_note"] = (
        f"{len(published)} recent uploads observed; latest: {published[0]}" if published
        else "recent posting cadence not observable"
    )
    out["confidence"] = "high" if views and subs else "low"
    return out


async def _analyze_themes(channel: dict, videos: list, campaign: dict) -> dict:
    titles = "\n".join(f"- {v.get('title', '')}" for v in videos[:12])
    campaign_desc = json.dumps({k: campaign.get(k) for k in ("product", "industry", "goal", "audience") if campaign.get(k)})
    system = (
        "You analyze a creator's content themes from real recent video titles and the channel "
        "description ONLY. Never invent videos or audience demographics. Return ONLY valid JSON."
    )
    user = (
        f"Channel: {channel.get('name')}\nDescription: {channel.get('description', '')[:400]}\n"
        f"Recent video titles:\n{titles}\n\n"
        f"Campaign context (may be empty): {campaign_desc}\n\n"
        'Return JSON: {"niche": "", "content_pillars": [], "top_recurring_themes": [], '
        '"emerging_themes": [], "declining_themes": [], "product_categories_discussed": [], '
        '"competitor_brands_mentioned": [], "typical_formats": [], '
        '"relevance_score": <0-100 topical match to the campaign context, or null if no campaign context>, '
        '"relevance_reason": ""}'
    )
    raw = await OpenAIChatClient().complete(system, user, max_tokens=700)
    parsed = _safe_json(raw)
    return parsed or {}


def _brand_safety_from_reputation(reputation) -> float | None:
    if not reputation or reputation.get("status") != "ok":
        return None
    tone = reputation.get("overall_tone", "mixed")
    risks = reputation.get("risk_timeline", []) or []
    high = sum(1 for r in risks if r.get("severity") == "high")
    med = sum(1 for r in risks if r.get("severity") == "medium")
    base = {"positive": 85.0, "mixed": 65.0, "negative": 35.0}.get(tone, 60.0)
    return max(0.0, base - high * 20 - med * 8)


def _sponsor_compat(sponsors, campaign: dict) -> float | None:
    if not sponsors or sponsors.get("status") not in ("ok", "no_visible_sponsors"):
        return None
    conflicts = sponsors.get("potential_competitor_conflicts", []) or []
    n = len(sponsors.get("sponsors", []) or [])
    if sponsors.get("status") == "no_visible_sponsors":
        return 70.0  # no visible history — neutral-positive, no conflicts
    base = 80.0 if n else 70.0
    return max(10.0, base - len(conflicts) * 25)


def _budget_fit(engagement: dict, campaign: dict):
    budget = campaign.get("budget")
    deliverable = campaign.get("deliverable", "integrated_segment")
    rate = estimate_rate(engagement.get("avg_views"), deliverable=deliverable)
    if rate.get("status") != "ok" or not budget:
        return None, rate
    try:
        budget = float(budget)
    except (TypeError, ValueError):
        return None, rate
    expected = rate["expected"]
    if expected <= 0:
        return None, rate
    ratio = budget / expected
    score = 100.0 if ratio >= 1.2 else 80.0 if ratio >= 0.9 else 55.0 if ratio >= 0.6 else 25.0
    return score, rate


def _safe_json(raw: str) -> dict:
    try:
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        return json.loads(m.group()) if m else {}
    except (json.JSONDecodeError, AttributeError):
        return {}
