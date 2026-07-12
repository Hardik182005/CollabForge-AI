import sys
import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.track02_content.script_generator import ScriptGenerator
from services.ai_providers.openai_client import OpenAIChatClient

router = APIRouter()
generator = ScriptGenerator()


class ScriptRequest(BaseModel):
    topic: str
    duration: int = 30
    style: str = "hooks"


class ViralityRequest(BaseModel):
    script_text: str
    platform: str = "instagram"


class LinkedInRequest(BaseModel):
    topic: str
    audience: str = "professionals"


class InstagramRequest(BaseModel):
    topic: str
    style: str = "engaging"


class InstagramImageRequest(BaseModel):
    topic: str
    caption: str = ""


@router.post("/generate-script")
async def generate_script(request: ScriptRequest):
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    result = await generator.generate(
        topic=request.topic,
        duration=request.duration,
        style=request.style,
    )
    return {"status": "success", **result}


@router.post("/predict-virality")
async def predict_virality(request: ViralityRequest):
    if not request.script_text:
        raise HTTPException(status_code=400, detail="script_text is required")
    result = await generator.predict_virality(
        script_text=request.script_text,
        platform=request.platform,
    )
    return {"status": "success", **result}


@router.post("/linkedin")
async def generate_linkedin(request: LinkedInRequest):
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    result = await generator.generate_linkedin_post(
        topic=request.topic,
        audience=request.audience,
    )
    return {"status": "success", **result}


@router.post("/instagram")
async def generate_instagram(request: InstagramRequest):
    if not request.topic:
        raise HTTPException(status_code=400, detail="Topic is required")
    result = await generator.generate_instagram_caption(
        topic=request.topic,
        style=request.style,
    )
    return {"status": "success", **result}


@router.post("/instagram-image")
async def generate_instagram_image(request: InstagramImageRequest):
    """Generate a matching Instagram post image with OpenAI for the given topic."""
    if not request.topic and not request.caption:
        raise HTTPException(status_code=400, detail="topic or caption is required")
    prompt = (
        f"A vibrant, modern, scroll-stopping Instagram post image about: {request.topic}. "
        "Social-media-ready, high quality, eye-catching composition, bold colors, "
        "no text overlay."
    )
    if request.caption:
        prompt += f" Visual mood from this caption: {request.caption[:200]}"

    b64 = await OpenAIChatClient().generate_image(prompt)
    if not b64:
        return {
            "status": "unavailable",
            "image_base64": None,
            "message": "Image generation unavailable (check OPENAI_API_KEY / image access).",
        }
    return {"status": "success", "image_base64": b64}
