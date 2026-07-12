import sys, os
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.security import validate_public_url, research_limiter
from services.generation.business_dna import analyze_business

router = APIRouter()


class BusinessAnalyzeRequest(BaseModel):
    website: str = Field(..., max_length=2000, examples=["https://www.boat-lifestyle.com"])
    business_name: str = Field("", max_length=200)
    context: str = Field("", max_length=1000, description="Product, industry, goal — anything extra")


@router.post("/analyze")
async def business_analyze(req: BusinessAnalyzeRequest, request: Request):
    """Scrape the public business website (Anakin URL Scraper) and extract an
    editable Business DNA profile. SSRF-guarded."""
    research_limiter.check(request)
    url = validate_public_url(req.website)
    extra = f"Business name: {req.business_name}. {req.context}".strip()
    return await analyze_business(url, extra)
