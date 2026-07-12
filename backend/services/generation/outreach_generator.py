"""Personalized outreach drafts. Drafting only — nothing is ever auto-sent."""
import json
import re

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.openai_client import OpenAIChatClient


async def generate_outreach(
    business_dna: dict, creator: dict, recent_content: list,
    campaign_goal: str, deliverables: str, budget_note: str, tone: str,
) -> dict:
    recent = "\n".join(
        f"- \"{v.get('title', '')}\" ({v.get('views', 'views unknown')} views, {v.get('published', '')})"
        for v in (recent_content or [])[:2]
    )
    system = (
        "You write influencer-collaboration outreach for a brand. Reference the creator's "
        "actual recent content provided. Professional, specific, no hype, no fake claims, "
        "no invented statistics. Return ONLY valid JSON."
    )
    user = (
        f"Business DNA: {json.dumps(business_dna)[:2000]}\n"
        f"Creator: {creator.get('name')} ({creator.get('handle', '')}), "
        f"subscribers: {creator.get('subscribers', 'unknown')}\n"
        f"Two recent posts to reference:\n{recent}\n"
        f"Campaign goal: {campaign_goal}\nDeliverables: {deliverables}\n"
        f"Budget approach: {budget_note}\nBrand tone: {tone}\n\n"
        'Return JSON with these string fields: "short_email" (subject + body, <150 words), '
        '"detailed_email" (subject + body with deliverables and next steps), '
        '"dm" (Instagram/LinkedIn DM, <80 words), "followup_1" (3-day follow-up), '
        '"followup_2" (7-day final follow-up), "negotiation_reply" (responding to a higher rate ask), '
        '"decline_hold" (polite decline/hold response).'
    )
    raw = await OpenAIChatClient().complete(system, user, max_tokens=1600)
    drafts = _safe_json(raw)
    if not drafts:
        return {"status": "error", "message": "Draft generation failed — retry"}
    return {
        "status": "ok",
        "sending_disabled": True,
        "note": "Drafts only. CollabForge never sends messages automatically — copy and send from your own account.",
        "drafts": drafts,
    }


def _safe_json(raw: str) -> dict:
    try:
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        return json.loads(m.group()) if m else {}
    except (json.JSONDecodeError, AttributeError):
        return {}
