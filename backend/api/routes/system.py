import sys, os
from fastapi import APIRouter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.anakin.capability_registry import capabilities

router = APIRouter()


@router.get("/capabilities")
async def get_capabilities():
    """What is genuinely usable right now — the frontend renders only enabled features."""
    data = await capabilities()
    return {"success": True, "data": data, "meta": {"status": "live"}, "warnings": []}
