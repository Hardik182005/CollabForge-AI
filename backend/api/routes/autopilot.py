"""Collab Autopilot: business brief → creator shortlist → outreach → campaign pack.

Streams 10 stages over SSE. Continues with partial results when a source
fails; failed live data is reported as failed, never swapped for invented data.
"""
import asyncio
import json
import sys, os
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.security import validate_public_url, research_limiter
from services.generation.business_dna import analyze_business
from services.generation.outreach_generator import generate_outreach
from services.generation.contract_generator import generate_contract
from services.generation.campaign_brief_generator import generate_brief
from services.research.dossier import build_dossier
from services.scoring.roi_scenarios import roi_scenario
from services.anakin.client import anakin_client, AnakinError
from services.ai_providers.openai_client import OpenAIChatClient

router = APIRouter()

STAGES = [
    "understand_business", "build_campaign_dna", "discover_creators",
    "research_candidates", "score_and_shortlist", "build_roi_scenarios",
    "draft_outreach", "draft_campaign_brief", "draft_contract",
    "generate_content_concept",
]


class AutopilotRequest(BaseModel):
    business_name: str = Field(..., min_length=1, max_length=200)
    website: str = Field("", max_length=2000)
    product: str = Field(..., min_length=1, max_length=500)
    industry: str = Field("", max_length=100)
    goal: str = Field(..., min_length=1, max_length=500)
    audience: str = Field("", max_length=300)
    geography: str = Field("", max_length=100)
    language: str = Field("", max_length=60)
    budget: Optional[float] = Field(None, ge=0)
    currency: str = Field("INR", max_length=8)
    deliverables: str = Field("one integrated video segment", max_length=300)
    candidate_creators: list = Field(default_factory=list, max_length=3)
    average_order_value: Optional[float] = Field(None, ge=0)


def _sse(stage: str, status: str, message: str, data: dict | None = None,
         provider: str = "", evidence_count: int = 0, error: str = "") -> str:
    payload = {
        "stage": stage, "status": status, "message": message,
        "provider": provider, "evidence_count": evidence_count,
    }
    if data:
        payload["data"] = data
    if error:
        payload["error"] = error
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


async def _run(req: AutopilotRequest) -> AsyncGenerator[str, None]:
    pack: dict = {"partial_failures": []}

    # 1 ── UNDERSTAND BUSINESS
    yield _sse("understand_business", "running", f"Analyzing {req.business_name}…")
    dna = {}
    if req.website:
        try:
            url = validate_public_url(req.website)
            result = await analyze_business(url, f"{req.product} | {req.industry} | {req.goal}")
            if result.get("status") == "ok":
                dna = result["business_dna"]
                yield _sse("understand_business", "done",
                           f"Extracted Business DNA from {url}", {"business_dna": dna},
                           provider="anakin_scrape", evidence_count=len(result.get("evidence", [])))
            else:
                pack["partial_failures"].append("business website analysis failed")
                yield _sse("understand_business", "partial", "Website analysis failed — continuing with your inputs only",
                           error=str(result.get("error", ""))[:200])
        except Exception as e:  # noqa: BLE001 — stage must not kill the stream
            pack["partial_failures"].append("business website analysis failed")
            yield _sse("understand_business", "partial", "Website analysis failed — continuing with your inputs only", error=str(e)[:200])
    else:
        yield _sse("understand_business", "done", "No website provided — using your inputs")
    dna = {**dna, "business_name": req.business_name, "product": req.product,
           "industry": req.industry, "stated_goal": req.goal}
    pack["business_dna"] = dna

    # 2 ── BUILD CAMPAIGN DNA
    yield _sse("build_campaign_dna", "running", "Structuring campaign parameters…")
    campaign = {
        "product": req.product, "industry": req.industry, "goal": req.goal,
        "audience": req.audience, "geography": req.geography, "language": req.language,
        "budget": req.budget, "currency": req.currency, "deliverable": "integrated_segment",
        "deliverables_text": req.deliverables,
    }
    pack["campaign"] = campaign
    yield _sse("build_campaign_dna", "done", "Campaign DNA ready", {"campaign": campaign})

    # 3 ── DISCOVER CREATORS
    yield _sse("discover_creators", "running", "Discovering candidate creators…")
    candidates = [str(c)[:120] for c in req.candidate_creators if str(c).strip()]
    if len(candidates) < 3:
        try:
            res = await anakin_client.search(
                f"List {4 - len(candidates)} popular YouTube creators for {req.audience or req.product} "
                f"in {req.geography or 'their market'} covering {req.product} / {req.industry}. Channel names only."
            )
            names = await _extract_names(res, exclude=candidates)
            candidates.extend(names[: 3 - len(candidates)])
            yield _sse("discover_creators", "done", f"Candidates: {', '.join(candidates)}",
                       {"candidates": candidates}, provider="anakin_search",
                       evidence_count=len(res.get("results", [])))
        except (AnakinError, Exception) as e:  # noqa: BLE001
            if candidates:
                yield _sse("discover_creators", "partial",
                           f"Discovery failed — continuing with provided candidate(s): {', '.join(candidates)}",
                           error=str(e)[:200])
            else:
                yield _sse("discover_creators", "failed", "No candidates available — cannot continue", error=str(e)[:200])
                yield _sse("complete", "failed", "Autopilot stopped: no creators to research", pack)
                return
    else:
        yield _sse("discover_creators", "done", f"Using provided candidates: {', '.join(candidates)}", {"candidates": candidates})

    # 4 ── RESEARCH CANDIDATES
    yield _sse("research_candidates", "running", f"Researching {len(candidates)} creators with live public data…")
    dossiers = []
    for name in candidates[:3]:
        try:
            d = await build_dossier(name, campaign)
            if d.get("status") == "ok":
                dossiers.append(d)
                yield _sse("research_candidates", "progress",
                           f"{d['overview']['name']}: {len(d.get('evidence', []))} evidence items, "
                           f"fit {d['fit_score'].get('score')}",
                           provider=d.get("data_method", ""), evidence_count=len(d.get("evidence", [])))
            else:
                pack["partial_failures"].append(f"research failed for {name}")
                yield _sse("research_candidates", "progress", f"{name}: {d.get('message', 'not found')}", error=d.get("status"))
        except Exception as e:  # noqa: BLE001
            pack["partial_failures"].append(f"research failed for {name}")
            yield _sse("research_candidates", "progress", f"{name}: research error", error=str(e)[:200])
    if not dossiers:
        yield _sse("research_candidates", "failed", "No creator could be researched with real data")
        yield _sse("complete", "failed", "Autopilot stopped: no evidence-backed creators", pack)
        return
    yield _sse("research_candidates", "done", f"Researched {len(dossiers)} creators")

    # 5 ── SCORE AND SHORTLIST
    yield _sse("score_and_shortlist", "running", "Ranking by explainable fit score…")
    # Rank by confidence first, then score; channels without meaningful
    # observable reach can't outrank well-evidenced creators on formula gaps.
    _conf = {"high": 2, "medium": 1, "low": 0}

    def _rank(d):
        fs = d["fit_score"]
        reach_ok = (d["overview"].get("subscribers") or 0) >= 5000
        return (reach_ok, _conf.get(fs.get("confidence"), 0), fs.get("score") or 0)

    dossiers.sort(key=_rank, reverse=True)
    top = dossiers[0]
    shortlist = [{
        "name": d["overview"]["name"], "fit": d["fit_score"].get("score"),
        "confidence": d["fit_score"].get("confidence"),
        "recommendation": d["fit_score"].get("recommendation"),
        "subscribers": d["overview"].get("subscribers"),
        "avg_views": d["engagement_signals"].get("avg_views"),
    } for d in dossiers]
    pack["shortlist"] = shortlist
    pack["selected"] = {"name": top["overview"]["name"], "fit_score": top["fit_score"],
                        "rate_estimate": top.get("rate_estimate")}
    pack["dossiers"] = [{k: d[k] for k in ("overview", "fit_score", "rate_estimate", "engagement_signals", "evidence")} for d in dossiers]
    yield _sse("score_and_shortlist", "done",
               f"Top pick: {top['overview']['name']} (fit {top['fit_score'].get('score')}, "
               f"{top['fit_score'].get('confidence')} confidence)", {"shortlist": shortlist})

    # 6 ── ROI SCENARIOS
    yield _sse("build_roi_scenarios", "running", "Building editable ROI scenario…")
    avg_views = top["engagement_signals"].get("avg_views") or 0
    cost = req.budget or (top.get("rate_estimate") or {}).get("expected") or 0
    if avg_views and cost:
        roi = roi_scenario(
            estimated_impressions=avg_views, engagement_rate_pct=3.0,
            click_through_rate_pct=1.0, conversion_rate_pct=2.0,
            average_order_value=req.average_order_value or 2000.0,
            campaign_cost=cost, currency=req.currency,
        )
        pack["roi"] = roi
        yield _sse("build_roi_scenarios", "done", "ROI scenario ready (all assumptions editable)", {"roi": roi})
    else:
        yield _sse("build_roi_scenarios", "partial", "Insufficient view/cost data for an ROI scenario — skipped")

    # 7 ── OUTREACH
    yield _sse("draft_outreach", "running", "Drafting personalized outreach (never auto-sent)…")
    try:
        outreach = await generate_outreach(
            dna, top["overview"], top.get("recent_content", [])[:2],
            req.goal, req.deliverables,
            f"budget around {req.currency} {req.budget:,.0f}" if req.budget else "request rate card",
            "professional and warm",
        )
        pack["outreach"] = outreach
        yield _sse("draft_outreach", "done", "Outreach drafts ready", {"outreach": outreach})
    except Exception as e:  # noqa: BLE001
        pack["partial_failures"].append("outreach drafting failed")
        yield _sse("draft_outreach", "failed", "Outreach drafting failed", error=str(e)[:200])

    # 8 ── BRIEF
    yield _sse("draft_campaign_brief", "running", "Drafting campaign brief…")
    try:
        brief = await generate_brief(dna, top["overview"], campaign)
        pack["brief"] = brief
        yield _sse("draft_campaign_brief", "done", "Campaign brief ready", {"brief": brief})
    except Exception as e:  # noqa: BLE001
        pack["partial_failures"].append("brief drafting failed")
        yield _sse("draft_campaign_brief", "failed", "Brief drafting failed", error=str(e)[:200])

    # 9 ── CONTRACT
    yield _sse("draft_contract", "running", "Drafting collaboration agreement template…")
    try:
        contract = await generate_contract({
            "brand": req.business_name, "creator": top["overview"]["name"],
            "campaign_name": f"{req.business_name} × {top['overview']['name']}",
            "deliverables": req.deliverables, "platforms": "YouTube",
            "compensation": f"{req.currency} {req.budget:,.0f}" if req.budget else "[TO BE COMPLETED]",
        })
        pack["contract"] = contract
        yield _sse("draft_contract", "done", "Contract template ready (review with counsel)", {"contract": contract})
    except Exception as e:  # noqa: BLE001
        pack["partial_failures"].append("contract drafting failed")
        yield _sse("draft_contract", "failed", "Contract drafting failed", error=str(e)[:200])

    # 10 ── CONTENT CONCEPT
    yield _sse("generate_content_concept", "running", "Generating sponsored content concept…")
    try:
        concept_raw = await OpenAIChatClient().complete(
            "You create sponsored-video concepts grounded in the creator's actual recent content "
            "titles and the campaign brief. No invented statistics. Return ONLY valid JSON.",
            f"Creator: {top['overview']['name']} — recent titles: "
            f"{[v.get('title') for v in top.get('recent_content', [])[:6]]}\n"
            f"Campaign: {json.dumps(campaign)[:800]}\n"
            'Return JSON: {"concept_title": "", "format": "", "hook": "", "beats": ["0-3s ...", ...], '
            '"integration_style": "", "cta": "", "disclosure": ""}',
            max_tokens=600,
        )
        import re as _re
        m = _re.search(r"\{.*\}", concept_raw or "", _re.DOTALL)
        pack["content_concept"] = json.loads(m.group()) if m else {}
        yield _sse("generate_content_concept", "done", "Content concept ready", {"concept": pack["content_concept"]})
    except Exception as e:  # noqa: BLE001
        pack["partial_failures"].append("content concept failed")
        yield _sse("generate_content_concept", "failed", "Content concept failed", error=str(e)[:200])

    yield _sse("complete", "done", "Campaign Launch Pack ready", pack)


@router.post("/run")
async def run_autopilot(req: AutopilotRequest, request: Request):
    research_limiter.check(request)
    return StreamingResponse(
        _run(req), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _extract_names(search_result: dict, exclude: list) -> list:
    corpus = json.dumps(search_result.get("results", []))[:5000]
    raw = await OpenAIChatClient().complete(
        "Extract YouTube creator/channel names mentioned in this search data. Return ONLY a JSON array of strings.",
        corpus, max_tokens=200,
    )
    import re as _re
    try:
        m = _re.search(r"\[.*\]", raw or "", _re.DOTALL)
        names = json.loads(m.group()) if m else []
    except (json.JSONDecodeError, AttributeError):
        names = []
    ex = {e.lower() for e in exclude}
    return [str(n)[:120] for n in names if isinstance(n, str) and n.lower() not in ex][:4]
