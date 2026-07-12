"""Campaign ROI scenario simulator — editable assumptions, not a forecast."""


def roi_scenario(
    estimated_impressions: int,
    engagement_rate_pct: float,
    click_through_rate_pct: float,
    conversion_rate_pct: float,
    average_order_value: float,
    campaign_cost: float,
    currency: str = "INR",
) -> dict:
    def run(mult: float) -> dict:
        impressions = int(estimated_impressions * mult)
        engagements = int(impressions * engagement_rate_pct / 100)
        clicks = int(impressions * click_through_rate_pct / 100)
        conversions = int(clicks * conversion_rate_pct / 100)
        revenue = round(conversions * average_order_value, 2)
        roas = round(revenue / campaign_cost, 2) if campaign_cost else None
        return {
            "impressions": impressions, "engagements": engagements,
            "clicks": clicks, "conversions": conversions,
            "revenue": revenue, "roas": roas,
        }

    break_even_cr = None
    clicks_base = estimated_impressions * click_through_rate_pct / 100
    if clicks_base and average_order_value:
        break_even_cr = round(campaign_cost / (clicks_base * average_order_value) * 100, 2)

    return {
        "label": "Scenario simulation with editable assumptions — not predicted or guaranteed revenue",
        "currency": currency,
        "assumptions": {
            "estimated_impressions": estimated_impressions,
            "engagement_rate_pct": engagement_rate_pct,
            "click_through_rate_pct": click_through_rate_pct,
            "conversion_rate_pct": conversion_rate_pct,
            "average_order_value": average_order_value,
            "campaign_cost": campaign_cost,
        },
        "scenarios": {
            "worst": run(0.6),
            "base": run(1.0),
            "best": run(1.5),
        },
        "break_even_conversion_rate_pct": break_even_cr,
    }
