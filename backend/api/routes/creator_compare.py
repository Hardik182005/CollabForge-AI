import asyncio
import sys, os
from typing import Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.security import research_limiter
from services.research.dossier import build_dossier
from api.routes.creator_research import CampaignContext

router = APIRouter()

_DIMS = ("fit", "reach", "avg_views", "engagement", "consistency", "brand_safety", "budget_fit")


class CompareRequest(BaseModel):
    creators: list = Field(..., min_length=2, max_length=3)
    campaign: Optional[CampaignContext] = None


@router.post("/compare")
async def compare_creators(req: CompareRequest, request: Request):
    """Compare up to three creators. Winners are only declared per dimension
    when both sides have real data; insufficient evidence → no winner."""
    research_limiter.check(request)
    campaign = req.campaign.model_dump() if req.campaign else None
    dossiers = await asyncio.gather(
        *[build_dossier(str(c)[:120], campaign) for c in req.creators],
        return_exceptions=True,
    )

    rows, failures = [], []
    for query, d in zip(req.creators, dossiers):
        if isinstance(d, Exception) or d.get("status") != "ok":
            failures.append({"creator": query, "reason": getattr(d, "get", lambda *_: "research failed")("message") if isinstance(d, dict) else "research failed"})
            continue
        fit = d.get("fit_score") or {}
        eng = d.get("engagement_signals") or {}
        comp = {c["name"]: c["score"] for c in fit.get("components", [])}
        rows.append({
            "creator": d["overview"].get("name", query),
            "handle": d["overview"].get("handle", ""),
            "fit": fit.get("score"),
            "fit_confidence": fit.get("confidence"),
            "reach": d["overview"].get("subscribers"),
            "avg_views": eng.get("avg_views"),
            "engagement": comp.get("engagement"),
            "consistency": comp.get("consistency"),
            "brand_safety": comp.get("brand_safety"),
            "budget_fit": comp.get("budget_fit"),
            "sponsor_conflicts": (d.get("sponsor_history") or {}).get("potential_competitor_conflicts", []),
            "recommendation": fit.get("recommendation"),
            "rate_expected": (d.get("rate_estimate") or {}).get("expected"),
            "evidence_count": len(d.get("evidence", [])),
        })

    winners = {}
    if len(rows) >= 2:
        def best(key, label, minimize=False):
            vals = [(r["creator"], r.get(key)) for r in rows if r.get(key) is not None]
            if len(vals) < 2:
                winners[label] = {"winner": None, "reason": "insufficient evidence on one or more creators"}
                return
            pick = min(vals, key=lambda x: x[1]) if minimize else max(vals, key=lambda x: x[1])
            winners[label] = {"winner": pick[0], "reason": f"{key} = {pick[1]}"}
        best("fit", "by_campaign_objective")
        best("reach", "best_reach")
        best("engagement", "best_engagement")
        best("brand_safety", "lowest_risk")
        # best value: highest fit per unit expected rate
        vals = [(r["creator"], r["fit"] / r["rate_expected"]) for r in rows if r.get("fit") and r.get("rate_expected")]
        winners["best_value"] = (
            {"winner": max(vals, key=lambda x: x[1])[0], "reason": "highest fit score per estimated cost"}
            if len(vals) >= 2 else {"winner": None, "reason": "insufficient rate/fit data"}
        )

    return {"status": "ok" if rows else "failed", "comparison": rows, "winners": winners, "failures": failures}
