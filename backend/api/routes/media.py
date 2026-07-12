"""Media routes (spec §27 /media/*).

GET  /api/v1/media/voices   → live ElevenLabs voices (or empty + reason)
POST /api/v1/media/voice    → generate a voiceover (base64 mp3) when configured
POST /api/v1/media/reel     → AI-assisted reel storyboard (scenes, prompts,
                              captions, narration). MP4 composition is only
                              claimed when a real render provider is configured.
"""
import asyncio
import base64
import json
import re
import sys, os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.elevenlabs_service import (
    generate_voiceover, list_elevenlabs_voices, AVAILABLE_VOICES,
)
from services.ai_providers.openai_client import openai_chat_client
from core.config import settings

router = APIRouter()


async def _complete_json(system: str, user: str, max_tokens: int = 900):
    raw = await openai_chat_client.complete(system, user, max_tokens=max_tokens)
    if not raw:
        return None
    raw = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


class VoiceRequest(BaseModel):
    script_text: str
    voice_id: str = "EXAVITQu4vr4xnSDxMaL"


class ReelRequest(BaseModel):
    script_text: str = ""
    topic: str = ""
    scenes: int = 5
    render_scenes: int = 3   # how many scenes to actually render as AI images


@router.get("/voices")
async def voices():
    v = await list_elevenlabs_voices()
    if not v:
        return {"success": True, "data": {"voices": []},
                "meta": {"status": "unavailable"},
                "warnings": [{"code": "ELEVENLABS_UNAVAILABLE",
                              "message": "ElevenLabs key not configured — voice generation disabled."}]}
    return {"success": True, "data": {"voices": v}, "meta": {"status": "live"}, "warnings": []}


@router.post("/voice")
async def voice(req: VoiceRequest):
    if not req.script_text.strip():
        raise HTTPException(status_code=400, detail="script_text is required")
    audio = await generate_voiceover(req.script_text, req.voice_id)
    if not audio:
        return {"success": False,
                "error": {"code": "ELEVENLABS_UNAVAILABLE",
                          "message": "ElevenLabs key not configured.", "retryable": False},
                "data": {"voices": AVAILABLE_VOICES}}
    return {"success": True,
            "data": {"audioBase64": base64.b64encode(audio).decode(),
                     "voiceId": req.voice_id, "textLength": len(req.script_text)},
            "meta": {"status": "live", "provider": "elevenlabs"}, "warnings": []}


@router.post("/reel")
async def reel(req: ReelRequest):
    """Storyboard for an AI-assisted reel. Honest about MP4 rendering."""
    basis = (req.script_text or req.topic or "").strip()
    if not basis:
        raise HTTPException(status_code=400, detail="Provide script_text or topic")
    n = max(3, min(req.scenes, 8))
    system = (
        "You are a short-form video director. Produce a storyboard for a ~30s "
        "vertical reel. Return ONLY valid JSON, no markdown."
    )
    user = (
        f"Basis:\n{basis[:800]}\n\n"
        f"Return JSON: {{\"scenes\": [{{\"n\": int, \"sceneText\": str, "
        f"\"imagePrompt\": str, \"narration\": str, \"caption\": str, "
        f"\"durationSec\": number}}] with exactly {n} scenes, "
        f"\"totalDurationSec\": number}}"
    )
    board = await _complete_json(system, user, max_tokens=900)
    if not board:
        return {"success": False,
                "error": {"code": "LLM_UNAVAILABLE",
                          "message": "Reel storyboard needs an LLM provider.", "retryable": False}}

    # Actually generate visuals: one AI image per scene (capped for cost/latency).
    scenes = (board.get("scenes") or [])
    to_render = scenes[:max(1, min(req.render_scenes, 4))]
    frames_generated = 0
    if settings.OPENAI_API_KEY:
        async def _render(scene):
            nonlocal frames_generated
            prompt = (scene.get("imagePrompt") or scene.get("sceneText") or basis)[:900]
            prompt += " — vertical 9:16 social reel frame, cinematic, high quality, no text overlay."
            b64 = await openai_chat_client.generate_image(prompt, size="1024x1024")
            if b64:
                scene["imageBase64"] = b64
                frames_generated += 1
        await asyncio.gather(*[_render(s) for s in to_render], return_exceptions=True)

    warnings = []
    if not frames_generated:
        warnings.append({"code": "IMAGES_UNAVAILABLE",
                         "message": "Scene images could not be generated (check OpenAI image access)."})
    return {
        "success": True,
        "data": {
            "label": "AI-assisted reel composition",
            "storyboard": board,
            "framesGenerated": frames_generated,
            "mp4": None,
            "renderNote": (f"{frames_generated} scene frame(s) generated with AI. "
                           "Download the frames + narration and assemble in your editor — "
                           "server-side MP4 stitching needs FFmpeg on the host."),
        },
        "meta": {"status": "live", "provider": settings.OPENAI_MODEL,
                 "framesGenerated": frames_generated},
        "warnings": warnings,
    }
