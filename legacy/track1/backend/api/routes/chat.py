import sys
import os
import re

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.groq_client import GroqClient

router = APIRouter()

SYSTEM_PROMPT = (
    "You are Creatrix AI's helpful in-app assistant. "
    "Creatrix AI is an AI influencer-intelligence and viral-content platform: "
    "it analyzes any creator's REAL YouTube data to compute a Ratefluencer Score, "
    "detects fake followers, predicts growth, matches brands, discovers live trends, "
    "and generates reel scripts, LinkedIn posts, Instagram captions, and ElevenLabs voiceovers. "
    "Answer concisely and helpfully, guiding the user through the dashboard. "
    "Reply in PLAIN TEXT only — do NOT use markdown, asterisks (*), pound/hash signs (#), "
    "bold, headings, or bullet symbols. Use plain sentences and, if listing, plain numbers like 1. 2. 3."
)


def _clean_reply(text: str) -> str:
    """Strip markdown so the chat bubble (rendered as plain text) never shows
    stray * or # characters."""
    if not text:
        return text
    # Drop heading markers at line starts (e.g. "## Title").
    text = re.sub(r"(?m)^\s{0,3}#{1,6}\s*", "", text)
    # Turn markdown bullets into a clean bullet glyph before removing markers.
    text = re.sub(r"(?m)^\s*[\*\-\+]\s+", "• ", text)
    # Remove emphasis wrappers and any remaining * / # characters.
    text = text.replace("**", "").replace("__", "")
    text = text.replace("*", "").replace("#", "")
    # Collapse excess blank lines left behind.
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class ChatRequest(BaseModel):
    message: str
    history: List = []


@router.post("/")
async def chat(request: ChatRequest):
    try:
        # Fold recent turns into the prompt so Groq has conversation context.
        convo = ""
        for turn in (request.history or [])[-8:]:
            role = turn.get("role", "user") if isinstance(turn, dict) else "user"
            content = turn.get("content", "") if isinstance(turn, dict) else str(turn)
            if content:
                convo += f"{'User' if role == 'user' else 'Assistant'}: {content}\n"
        user = (convo + f"User: {request.message}\nAssistant:") if convo else request.message

        # Groq Llama 3.3 70B — fastest provider, ideal for chat (OpenAI fallback built in).
        reply = await GroqClient().complete(SYSTEM_PROMPT, user, max_tokens=500)
        if not reply or not reply.strip():
            reply = "I'm here to help! Please try again in a moment."
        return {"status": "success", "reply": _clean_reply(reply)}
    except Exception:
        return {
            "status": "success",
            "reply": "I'm here to help you navigate Creatrix AI! Please try again in a moment.",
        }
