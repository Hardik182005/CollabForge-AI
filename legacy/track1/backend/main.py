import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.routes import influencer, content, trends, agent, virality, reports, chat

app = FastAPI(
    title="Creatrix AI — Ratefluencer API",
    version="2.0.0",
    description="AI-powered influencer intelligence + viral content platform — Ratefluencer AI Hackathon 2026",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(influencer.router, prefix="/api/v1/influencer", tags=["Track01 — Influencer Intelligence"])
app.include_router(content.router,    prefix="/api/v1/content",    tags=["Track02 — Content"])
app.include_router(trends.router,     prefix="/api/v1/trends",     tags=["Track02 — Trends"])
app.include_router(virality.router,   prefix="/api/v1/virality",   tags=["Track02 — Virality & Voiceover"])
app.include_router(reports.router,    prefix="/api/v1/reports",    tags=["Reports & Library"])
app.include_router(agent.router,      prefix="/api/v1/agent",      tags=["Grand Challenge — Autonomous Agent"])
app.include_router(chat.router,       prefix="/api/v1/chat",       tags=["Help Chatbot"])


@app.on_event("startup")
async def startup_event():
    gemini_ok = bool(settings.GEMINI_API_KEY)
    groq_ok = bool(settings.GROQ_API_KEY) and not settings.GROQ_API_KEY.startswith("gsk_...")
    el_ok = bool(settings.ELEVENLABS_API_KEY)
    print("=" * 60)
    print("Creatrix AI — Ratefluencer API v2.0")
    print(f"  Gemini      : {'OK' if gemini_ok else 'fallback mode'}")
    print(f"  Groq        : {'OK' if groq_ok else 'fallback mode'}")
    print(f"  ElevenLabs  : {'OK' if el_ok else 'not configured'}")
    print(f"  Port        : {settings.PORT}")
    print("=" * 60)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "Creatrix AI — Ratefluencer API",
        "version": "2.0.0",
        "tracks": ["Track01: Influencer Intelligence", "Track02: Viral Creator Agent", "Grand Challenge: Autonomous Agent"],
    }


@app.get("/")
def root():
    return {
        "name": "Creatrix AI — Ratefluencer API",
        "docs": "/docs",
        "health": "/health",
        "hackathon": "Ratefluencer AI Hackathon 2026",
        "endpoints": {
            "influencer_analyze":  "POST /api/v1/influencer/analyze",
            "influencer_growth":   "POST /api/v1/influencer/growth",
            "influencer_auth":     "POST /api/v1/influencer/authenticity",
            "brand_match":         "POST /api/v1/influencer/brands",
            "reports":             "GET  /api/v1/reports",
            "save_report":         "POST /api/v1/reports/save",
            "trends":              "POST /api/v1/trends/discover",
            "script":              "POST /api/v1/content/generate-script",
            "linkedin":            "POST /api/v1/content/linkedin",
            "instagram":           "POST /api/v1/content/instagram",
            "virality":            "POST /api/v1/virality/predict",
            "voiceover":           "POST /api/v1/virality/voiceover",
            "library":             "GET  /api/v1/reports/library",
            "save_content":        "POST /api/v1/reports/library/save",
            "agent":               "POST /api/v1/agent/run",
        },
    }
