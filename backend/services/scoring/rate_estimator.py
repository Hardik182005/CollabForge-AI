"""Transparent collaboration rate range from observable data.

This is an ESTIMATE derived from public benchmarks (CPM-style ranges by
deliverable), never a confirmed creator quotation. All assumptions are
returned with the result.
"""

# Indicative INR CPM bands per 1000 views for sponsored placements on YouTube
# (wide on purpose; industry rates vary hugely). Sources: public agency
# benchmark ranges; treated as assumptions, shown to the user.
_DELIVERABLE_CPM_INR = {
    "dedicated_video": (900, 2500),
    "integrated_segment": (400, 1200),
    "youtube_short": (250, 800),
    "instagram_reel": (300, 900),
    "mention": (150, 450),
}


def estimate_rate(
    avg_views: int | None,
    deliverable: str = "integrated_segment",
    currency: str = "INR",
    usage_rights: bool = False,
    exclusivity: bool = False,
) -> dict:
    deliverable = deliverable if deliverable in _DELIVERABLE_CPM_INR else "integrated_segment"
    if not avg_views:
        return {
            "status": "unavailable",
            "message": "Recent average views unavailable — cannot estimate a defensible range.",
            "deliverable": deliverable,
        }
    lo_cpm, hi_cpm = _DELIVERABLE_CPM_INR[deliverable]
    low = int(avg_views / 1000 * lo_cpm)
    high = int(avg_views / 1000 * hi_cpm)
    expected = int((low + high) / 2)

    multiplier_notes = []
    if usage_rights:
        low, expected, high = int(low * 1.2), int(expected * 1.25), int(high * 1.3)
        multiplier_notes.append("paid usage rights: +20–30%")
    if exclusivity:
        low, expected, high = int(low * 1.15), int(expected * 1.2), int(high * 1.25)
        multiplier_notes.append("category exclusivity: +15–25%")

    return {
        "status": "ok",
        "label": "Estimated range — not a confirmed creator quotation",
        "currency": currency,
        "low": low,
        "expected": expected,
        "high": high,
        "deliverable": deliverable,
        "assumptions": [
            f"Based on recent average views of {avg_views:,}",
            f"CPM band for {deliverable}: ₹{lo_cpm}–₹{hi_cpm} per 1000 views (public agency benchmark ranges)",
            *multiplier_notes,
            "Actual rates depend on the creator's own rate card, season, and negotiation",
        ],
        "usage_rights_included": usage_rights,
        "exclusivity_included": exclusivity,
        "confidence": "medium" if avg_views > 10000 else "low",
    }
