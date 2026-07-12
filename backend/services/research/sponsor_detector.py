"""Sponsor history from observable public signals: video titles + web search."""
import json
import re

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.anakin.client import anakin_client, AnakinError
from services.anakin.normalizer import from_search
from services.ai_providers.openai_client import OpenAIChatClient
from models.evidence import dedupe_evidence


async def detect_sponsors(creator_name: str, videos: list) -> dict:
    evidence = []
    try:
        res = await anakin_client.search(
            f"Which brands has {name_safe(creator_name)} visibly sponsored, promoted or partnered with "
            f"in videos or posts? List brand names with the video/post if known."
        )
        evidence = from_search(res, "web")
    except AnakinError:
        pass

    titles = "\n".join(f"- {v.get('title', '')}" for v in (videos or [])[:12])
    corpus = "\n".join(
        f"- [{e.source}] {e.title}: {e.snippet} ({e.url})" for e in evidence
    )[:7000]

    if not corpus and not titles:
        return {"status": "insufficient_evidence", "sponsors": [], "evidence": []}

    system = (
        "You identify VISIBLE sponsorship/promotion signals for a creator using ONLY the provided "
        "evidence and video titles. Only list a brand when the evidence explicitly indicates a "
        "sponsorship, promotion, unboxing-with-partnership, or brand campaign. Never guess. "
        "Return ONLY valid JSON."
    )
    user = (
        f"Creator: {creator_name}\nRecent video titles:\n{titles}\n\nWeb evidence:\n{corpus}\n\n"
        'Return JSON: {"sponsors": [{"brand": "...", "approx_date": "... or unknown", '
        '"context": "which video/post or source", "category": "...", "repeated": bool, '
        '"evidence_url": "url from the evidence or empty"}], '
        '"potential_competitor_conflicts": ["..."], "confidence": "high|medium|low"}'
    )
    raw = await OpenAIChatClient().complete(system, user, max_tokens=800)
    parsed = _safe_json(raw)
    sponsors = parsed.get("sponsors", []) if parsed else []
    return {
        "status": "ok" if sponsors else "no_visible_sponsors",
        "label": "Visible public sponsorship signals — not a complete commercial history",
        "sponsors": sponsors,
        "potential_competitor_conflicts": parsed.get("potential_competitor_conflicts", []) if parsed else [],
        "confidence": (parsed or {}).get("confidence", "low"),
        "evidence": [e.model_dump() for e in dedupe_evidence(evidence)[:15]],
    }


def name_safe(name: str) -> str:
    return re.sub(r"[^\w\s@.-]", "", name or "")[:80]


def _safe_json(raw: str) -> dict:
    try:
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        return json.loads(m.group()) if m else {}
    except (json.JSONDecodeError, AttributeError):
        return {}
