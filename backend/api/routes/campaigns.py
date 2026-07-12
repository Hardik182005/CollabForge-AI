import sys, os
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.security import generation_limiter
from services.scoring.roi_scenarios import roi_scenario
from services.generation.outreach_generator import generate_outreach
from services.generation.contract_generator import generate_contract
from services.generation.campaign_brief_generator import generate_brief
from services.persistence.repository import get_repository

router = APIRouter()


# ── ROI scenario ─────────────────────────────────────────────────────────

class RoiRequest(BaseModel):
    estimated_impressions: int = Field(..., ge=0, le=2_000_000_000)
    engagement_rate_pct: float = Field(3.0, ge=0, le=100)
    click_through_rate_pct: float = Field(1.0, ge=0, le=100)
    conversion_rate_pct: float = Field(2.0, ge=0, le=100)
    average_order_value: float = Field(..., ge=0)
    campaign_cost: float = Field(..., ge=0)
    currency: str = Field("INR", max_length=8)


@router.post("/roi-scenario")
async def campaign_roi(req: RoiRequest):
    return roi_scenario(**req.model_dump())


# ── Outreach ─────────────────────────────────────────────────────────────

class OutreachRequest(BaseModel):
    business_dna: dict = {}
    creator: dict = {}
    recent_content: list = []
    campaign_goal: str = Field("", max_length=500)
    deliverables: str = Field("", max_length=500)
    budget_note: str = Field("request creator's rate card", max_length=300)
    tone: str = Field("professional and warm", max_length=100)


@router.post("/outreach")
async def campaign_outreach(req: OutreachRequest, request: Request):
    generation_limiter.check(request)
    return await generate_outreach(
        req.business_dna, req.creator, req.recent_content,
        req.campaign_goal, req.deliverables, req.budget_note, req.tone,
    )


# ── Contract ─────────────────────────────────────────────────────────────

class ContractRequest(BaseModel):
    fields: dict = Field(
        default_factory=dict,
        description="Parties, campaign name, deliverables, compensation, dates, usage rights, exclusivity, etc.",
    )


@router.post("/contract")
async def campaign_contract(req: ContractRequest, request: Request):
    generation_limiter.check(request)
    return await generate_contract(req.fields)


# ── Brief ────────────────────────────────────────────────────────────────

class BriefRequest(BaseModel):
    business_dna: dict = {}
    creator: dict = {}
    campaign: dict = {}


@router.post("/brief")
async def campaign_brief(req: BriefRequest, request: Request):
    generation_limiter.check(request)
    return await generate_brief(req.business_dna, req.creator, req.campaign)


# ── Campaign Rooms CRUD ──────────────────────────────────────────────────

class CampaignRoomCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    business_dna: dict = {}
    shortlist: list = []
    comparison: Optional[dict] = None
    selected_creator: Optional[dict] = None
    dossier: Optional[dict] = None
    brief: Optional[dict] = None
    outreach: Optional[dict] = None
    contract: Optional[dict] = None
    content_pack: Optional[dict] = None
    roi: Optional[dict] = None
    status: str = "draft"
    activity: list = []


class CampaignRoomUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    business_dna: Optional[dict] = None
    shortlist: Optional[list] = None
    comparison: Optional[dict] = None
    selected_creator: Optional[dict] = None
    dossier: Optional[dict] = None
    brief: Optional[dict] = None
    outreach: Optional[dict] = None
    contract: Optional[dict] = None
    content_pack: Optional[dict] = None
    roi: Optional[dict] = None
    status: Optional[str] = None
    activity: Optional[list] = None


@router.get("")
async def list_campaigns():
    return {"status": "ok", "campaigns": get_repository().list()}


@router.post("")
async def create_campaign(req: CampaignRoomCreate):
    record = get_repository().create(req.model_dump())
    return {"status": "ok", "campaign": record}


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    rec = get_repository().get(campaign_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"status": "ok", "campaign": rec}


@router.put("/{campaign_id}")
async def update_campaign(campaign_id: str, req: CampaignRoomUpdate):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    rec = get_repository().update(campaign_id, updates)
    if not rec:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return {"status": "ok", "campaign": rec}
