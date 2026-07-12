import httpx
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import settings

VOICE_ID_DEFAULT = "EXAVITQu4vr4xnSDxMaL"  # Rachel

async def generate_voiceover(text: str, voice_id: str = VOICE_ID_DEFAULT) -> bytes:
    if not settings.ELEVENLABS_API_KEY:
        return b""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text[:2500],
        "model_id": "eleven_turbo_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            return r.content
    except Exception:
        return b""

# Static fallback only — used when no key is set or the live call fails.
AVAILABLE_VOICES = [
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Rachel", "style": "calm"},
    {"id": "TxGEqnHWrfWFTfGW9XjX", "name": "Josh", "style": "deep"},
    {"id": "AZnzlk1XvdvUeBnXmlld", "name": "Domi", "style": "energetic"},
    {"id": "MF3mGyEYCl7XYWbV9V6O", "name": "Elli", "style": "friendly"},
]


async def list_elevenlabs_voices() -> list:
    """Return the account's LIVE ElevenLabs voices. No presets — these come
    straight from the ElevenLabs API. Falls back to the static list only when
    the key is missing or the call fails."""
    if not settings.ELEVENLABS_API_KEY:
        return AVAILABLE_VOICES
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
            )
            r.raise_for_status()
            data = r.json()
            voices = []
            for v in data.get("voices", []):
                vid = v.get("voice_id")
                if not vid:
                    continue
                labels = v.get("labels") or {}
                style = labels.get("description") or labels.get("accent") or labels.get("use_case") or "neutral"
                voices.append({"id": vid, "name": v.get("name", "Voice"), "style": style})
            return voices or AVAILABLE_VOICES
    except Exception:
        return AVAILABLE_VOICES
