import sys
import os
import base64
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.gemini_client import GeminiClient
from services.elevenlabs_service import generate_voiceover, list_elevenlabs_voices, AVAILABLE_VOICES

router = APIRouter()
gemini = GeminiClient()


class ViralityRequest(BaseModel):
    hook: str = ""
    story: str = ""
    cta: str = ""
    platform: str = "instagram"
    posting_time: str = "18:00"
    script_text: str = ""


class VoiceoverRequest(BaseModel):
    script_text: str
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"


@router.post("/predict")
async def predict_virality(req: ViralityRequest):
    combined = req.script_text or f"{req.hook} {req.story} {req.cta}"
    if not combined.strip():
        raise HTTPException(status_code=400, detail="Provide script_text or hook/story/cta")

    system = (
        "You are a content analyst. Give a heuristic assessment of short-form content. "
        "This is a forecast with stated reasoning, not a measured prediction — do not "
        "output expected view/like counts. Return ONLY valid JSON, no markdown."
    )
    user = (
        f"Assess this {req.platform} content posted at {req.posting_time}:\n"
        f"{combined[:600]}\n\n"
        "Return JSON: {\"virality_score\": int 0-100, "
        "\"hook_strength\": int 0-100, \"content_novelty\": int 0-100, "
        "\"platform_fit\": int 0-100, \"grade\": \"A/B/C/D\", "
        "\"confidence\": \"high|medium|low\", "
        "\"contributing_factors\": [\"...\"], "
        "\"explanation\": \"one sentence\", \"tips\": [\"tip1\", \"tip2\"]}"
    )
    result = await gemini.complete_json(system, user, max_tokens=600)
    if not result:
        return {
            "status": "unavailable",
            "message": "Virality evaluation needs an LLM provider. No score was generated.",
        }
    return {
        "status": "success",
        "label": "Heuristic forecast by an LLM — not a measured accuracy claim",
        **result,
    }


@router.post("/voiceover")
async def generate_reel_voiceover(req: VoiceoverRequest):
    if not req.script_text.strip():
        raise HTTPException(status_code=400, detail="script_text is required")
    audio_bytes = await generate_voiceover(req.script_text, req.voice_id)
    if not audio_bytes:
        return {
            "status": "unavailable",
            "message": "ElevenLabs key not configured. Add ELEVENLABS_API_KEY to .env",
            "audio_base64": None,
            "voices": AVAILABLE_VOICES,
        }
    audio_b64 = base64.b64encode(audio_bytes).decode()
    return {
        "status": "success",
        "audio_base64": audio_b64,
        "voice_id": req.voice_id,
        "text_length": len(req.script_text),
        "voices": AVAILABLE_VOICES,
    }


@router.get("/voices")
async def list_voices():
    # Live from the ElevenLabs account — no hardcoded presets.
    return {"status": "success", "voices": await list_elevenlabs_voices()}
