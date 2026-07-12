"""Explainable 0–100 Creator Fit score.

Weights: 25% audience/topic relevance, 20% engagement quality,
15% content consistency, 15% brand-safety signal, 15% sponsor compatibility,
10% budget fit. Missing data reduces confidence — it is never replaced
with fabricated values. Computed in Python; the formula is returned with
the result.
"""

WEIGHTS = {
    "relevance": 0.25,
    "engagement": 0.20,
    "consistency": 0.15,
    "brand_safety": 0.15,
    "sponsor_compatibility": 0.15,
    "budget_fit": 0.10,
}

FORMULA = "score = 25%·relevance + 20%·engagement + 15%·consistency + 15%·brand_safety + 15%·sponsor_compat + 10%·budget_fit (missing components are excluded and lower confidence)"


def _engagement_component(subscribers: int, avg_views: int) -> tuple:
    """Views-to-subscribers ratio → 0-100. Returns (score, note) or (None, reason)."""
    if not subscribers or not avg_views:
        return None, "subscriber or view data unavailable"
    ratio = avg_views / subscribers
    # 20%+ views/subs is excellent for large channels; scale saturating at 0.35
    score = min(100.0, (ratio / 0.35) * 100.0)
    return round(score, 1), f"avg views / subscribers = {ratio:.3f}"


def _consistency_component(videos: list) -> tuple:
    views = [v.get("views") or 0 for v in (videos or []) if (v.get("views") or 0) > 0]
    if len(views) < 4:
        return None, "fewer than 4 recent videos with view counts"
    mean = sum(views) / len(views)
    var = sum((x - mean) ** 2 for x in views) / len(views)
    cv = (var ** 0.5) / mean if mean else 1.0
    # coefficient of variation 0 → 100 pts, 1.5+ → 0 pts
    score = max(0.0, min(100.0, 100.0 * (1 - cv / 1.5)))
    return round(score, 1), f"view-count coefficient of variation = {cv:.2f} across {len(views)} videos"


def compute_fit(
    relevance: float | None,
    engagement_inputs: dict,
    videos: list,
    brand_safety: float | None,
    sponsor_compatibility: float | None,
    budget_fit: float | None,
) -> dict:
    components = {}
    missing = []

    def add(name, value, note):
        if value is None:
            missing.append({"component": name, "reason": note})
        else:
            components[name] = {"score": round(float(value), 1), "weight": WEIGHTS[name], "note": note}

    add("relevance", relevance, "LLM-graded topical match between creator content and campaign, over collected evidence")
    eng, eng_note = _engagement_component(
        engagement_inputs.get("subscribers") or 0, engagement_inputs.get("avg_views") or 0
    )
    add("engagement", eng, eng_note)
    cons, cons_note = _consistency_component(videos)
    add("consistency", cons, cons_note)
    add("brand_safety", brand_safety, "derived from public sentiment signal balance")
    add("sponsor_compatibility", sponsor_compatibility, "derived from visible sponsor history vs campaign category")
    add("budget_fit", budget_fit, "estimated rate range vs stated budget")

    if not components:
        return {
            "score": None, "confidence": "none", "formula": FORMULA,
            "components": [], "missing_data": missing,
            "recommendation": "insufficient_data",
        }

    total_weight = sum(c["weight"] for c in components.values())
    score = sum(c["score"] * c["weight"] for c in components.values()) / total_weight

    present = len(components)
    confidence = "high" if present >= 5 else "medium" if present >= 3 else "low"
    recommendation = (
        "shortlist" if score >= 70 and confidence != "low"
        else "consider" if score >= 50
        else "review_manually" if confidence == "low"
        else "pass"
    )
    return {
        "score": round(score),
        "confidence": confidence,
        "formula": FORMULA,
        "components": [
            {"name": k, **v} for k, v in components.items()
        ],
        "missing_data": missing,
        "recommendation": recommendation,
    }
