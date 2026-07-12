"""Campaign brief generation grounded in Business DNA + creator research."""
import json
import re

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.openai_client import OpenAIChatClient


async def generate_brief(business_dna: dict, creator: dict, campaign: dict) -> dict:
    system = (
        "You write influencer campaign briefs. Ground everything in the provided business "
        "DNA and campaign inputs. Claims to avoid MUST include anything not in "
        "claims_not_to_invent. No invented statistics. Return ONLY valid JSON."
    )
    user = (
        f"Business DNA: {json.dumps(business_dna)[:2000]}\n"
        f"Creator: {json.dumps(creator)[:800]}\n"
        f"Campaign inputs: {json.dumps(campaign)[:1200]}\n\n"
        'Return JSON: {"objective": "", "product_context": "", "audience": "", '
        '"single_minded_message": "", "mandatory_points": [], "claims_to_avoid": [], '
        '"deliverables": [], "creative_direction": "", "suggested_hooks": [], '
        '"suggested_video_structure": ["0-3s ...", "3-10s ..."], "cta": "", '
        '"hashtags": [], "disclosure_requirement": "", "timeline": [], '
        '"approval_process": "", "tracking_links": ["[UTM LINK PLACEHOLDER]"], '
        '"success_metrics": []}'
    )
    raw = await OpenAIChatClient().complete(system, user, max_tokens=1400)
    brief = _safe_json(raw)
    if not brief:
        return {"status": "error", "message": "Brief generation failed — retry"}
    return {"status": "ok", "editable": True, "brief": brief}


def _safe_json(raw: str) -> dict:
    try:
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        return json.loads(m.group()) if m else {}
    except (json.JSONDecodeError, AttributeError):
        return {}
