"""Business DNA: scrape the public business website via Anakin, structure with LLM."""
import json
import re

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.anakin.client import anakin_client, AnakinError
from services.ai_providers.openai_client import OpenAIChatClient
from models.evidence import Evidence

_SCRAPE_PROMPT = (
    "Extract as JSON: business_name, what_they_sell (short), main_products_or_services "
    "(array), primary_customer, price_positioning (budget/mid/premium if inferable), "
    "value_proposition, brand_tone, geographic_focus, notable_claims (array of explicit "
    "claims made on the page). Only include what is visible on the page."
)


async def analyze_business(url: str, extra_context: str = "") -> dict:
    try:
        res = await anakin_client.scrape(url, use_browser=True, json_prompt=_SCRAPE_PROMPT)
    except AnakinError as e:
        return {"status": "error", "error": e.to_dict()}

    gen = res.get("generatedJson") or {}
    data = gen.get("data") if isinstance(gen, dict) else None
    markdown = (res.get("markdown") or "")[:6000]
    if not data and not markdown:
        return {"status": "error", "error": {"message": "Website returned no readable content"}}

    system = (
        "You build a concise Business DNA profile from scraped website content. "
        "Use ONLY the provided content; leave fields empty rather than inventing. "
        "notable_claims must be claims the site itself makes — the campaign must not "
        "invent claims beyond these. Return ONLY valid JSON."
    )
    user = (
        f"Scraped structured data: {json.dumps(data or {})[:3000]}\n\n"
        f"Page text excerpt:\n{markdown[:4000]}\n\n"
        f"Extra context from the user: {extra_context[:500]}\n\n"
        'Return JSON: {"business_name": "", "what_they_sell": "", "primary_customer": "", '
        '"price_positioning": "", "value_proposition": "", "brand_tone": "", '
        '"product_categories": [], "geographic_relevance": "", '
        '"likely_campaign_objectives": [], "claims_not_to_invent": []}'
    )
    raw = await OpenAIChatClient().complete(system, user, max_tokens=800)
    dna = _safe_json(raw)
    if not dna:
        return {"status": "error", "error": {"message": "Could not structure business profile"}}

    evidence = Evidence(
        source="web", source_type="page", title=dna.get("business_name") or url,
        url=url, snippet=(markdown or str(data))[:400],
        data_method="anakin_scrape", confidence="high",
    )
    return {
        "status": "ok",
        "editable": True,
        "note": "Extracted from the public website — review and edit before continuing.",
        "business_dna": dna,
        "evidence": [evidence.model_dump()],
    }


def _safe_json(raw: str) -> dict:
    try:
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        return json.loads(m.group()) if m else {}
    except (json.JSONDecodeError, AttributeError):
        return {}
