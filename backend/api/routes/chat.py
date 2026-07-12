import sys
import os
import re

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.ai_providers.openai_client import openai_chat_client
from services.ai_providers.groq_client import GroqClient

router = APIRouter()

SYSTEM_PROMPT = (
    "You are Forge, the witty AI sidekick living inside CollabForge AI. "
    "Personality: friendly, a little cheeky, quick with a light joke — but genuinely helpful "
    "and never sarcastic to the point of being unhelpful. Keep it snappy (2-4 sentences usually). "
    "\n\nWhat CollabForge AI is (tagline: Research. Score. Create. Close. — live creator "
    "intelligence powered by Anakin): a single web app with two workspaces you switch between "
    "in the left sidebar.\n"
    "CREATOR STUDIO: Trend Discovery (live topics via Anakin Search), Script Studio (15/30/60s "
    "hook-story-value-CTA scripts), Hook Lab (6 hooks with why-they-work), Social Content Pack "
    "(YouTube/IG/LinkedIn/hashtags/thumbnail text), Voice Studio (ElevenLabs voiceover), Reel "
    "Builder (AI-assisted reel with generated scene images), Virality Evaluation, Saved Content.\n"
    "BRAND INTELLIGENCE: Discover Creators (search or discover by topic), Creator Research "
    "(evidence-backed dossier: overview, recent content, engagement, public sentiment, sponsor "
    "history, an explainable Brand Fit Score with weighted components, estimated collaboration "
    "range, evidence library), Compare Creators, Campaign Planner (Business DNA from the public "
    "website via Anakin Universal Scraper), ROI Scenarios (editable assumptions), Outreach Studio "
    "(personalized drafts, never auto-sent), Contract Builder (editable template, not legal "
    "advice), Campaign Room (saves everything), and COLLAB AUTOPILOT — a 6-step wizard (Business, "
    "Audience, Goal, Budget, Creator strategy, Review) that then streams a 10-stage live pipeline.\n"
    "THE LIVE PIPELINE: your query -> source router -> Anakin (Wire + Universal Scraper) -> "
    "normalized evidence -> AI reasoning/scoring -> campaign output. Everything traces back to "
    "real public evidence with source badges and confidence levels; estimates are labelled as "
    "estimates. Data comes from Anakin (YouTube, Reddit, Google News, public websites), reasoning "
    "from OpenAI, voice from ElevenLabs.\n"
    "Tips you can give: to try it, tell them to click 'Explore Brand Intelligence' and search a "
    "creator like Technical Guruji, or 'Open Creator Studio' and discover a trend. Autopilot is "
    "under Brand Intelligence in the sidebar.\n\n"
    "STYLE RULES (important): reply in PLAIN TEXT only. Absolutely no markdown — no asterisks (*), "
    "no pound/hash signs (#), no bold, no headings, no bullet symbols. If you list things, use "
    "plain numbers like 1. 2. 3. Since your words may be read aloud by a voice, keep sentences "
    "natural and speakable. If you don't know something, say so with a smile."
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
    page: str = ""


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
        page = getattr(request, "page", "") or ""
        ctx = f"(The user is currently on: {page})\n" if page else ""
        user = ctx + ((convo + f"User: {request.message}\nAssistant:") if convo else request.message)

        # OpenAI primary (per product), Groq fallback if the key is missing.
        reply = await openai_chat_client.complete(SYSTEM_PROMPT, user, max_tokens=400)
        if not reply or not reply.strip():
            reply = await GroqClient().complete(SYSTEM_PROMPT, user, max_tokens=400)
        if not reply or not reply.strip():
            reply = "My brain skipped a beat — mind trying that again?"
        return {"status": "success", "reply": _clean_reply(reply)}
    except Exception:
        return {
            "status": "success",
            "reply": "Oops, I tripped over a wire (not an Anakin one). Try me again in a sec!",
        }
