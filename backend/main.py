import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings, cors_origins, validate_startup
from api.routes import (
    system, business, creator_research, creator_compare, campaigns,
    autopilot, content, trends, virality, reports, chat, pipeline, media,
)

app = FastAPI(
    title="CollabForge AI API",
    version="1.0.0",
    description=(
        "Research. Score. Create. Close. — two-sided platform for creators "
        "(trend research + content generation) and businesses (influencer "
        "research, scoring, outreach, contracts, campaign packs). "
        "Live data via Anakin Wire / Universal Scraper / Search."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def limit_body_size(request, call_next):
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > 1_000_000:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=413, content={"detail": "Request body too large"})
    return await call_next(request)


# ── Brand Deal Desk + platform ──────────────────────────────────────────
app.include_router(system.router,           prefix="/api/v1/system",    tags=["System"])
app.include_router(pipeline.router,         prefix="/api/v1/pipeline",  tags=["Live Pipeline"])
app.include_router(media.router,            prefix="/api/v1/media",     tags=["Media"])
app.include_router(business.router,         prefix="/api/v1/business",  tags=["Business DNA"])
app.include_router(creator_research.router, prefix="/api/v1/creators",  tags=["Creator Research"])
app.include_router(creator_compare.router,  prefix="/api/v1/creators",  tags=["Creator Comparison"])
app.include_router(campaigns.router,        prefix="/api/v1/campaigns", tags=["Campaigns"])
app.include_router(autopilot.router,        prefix="/api/v1/autopilot", tags=["Collab Autopilot"])

# ── Creator Studio (preserved + cleaned) ────────────────────────────────
app.include_router(content.router,  prefix="/api/v1/content",  tags=["Creator Studio — Content"])
app.include_router(trends.router,   prefix="/api/v1/trends",   tags=["Creator Studio — Trends"])
app.include_router(virality.router, prefix="/api/v1/virality", tags=["Creator Studio — Voice & Evaluation"])
app.include_router(reports.router,  prefix="/api/v1/reports",  tags=["Reports & Library"])
app.include_router(chat.router,     prefix="/api/v1/chat",     tags=["Help Chatbot"])


@app.on_event("startup")
async def startup_event():
    status = validate_startup()
    print("=" * 60)
    print("CollabForge AI API v1.0 — Research. Score. Create. Close.")
    for name, ok in status.items():
        print(f"  {name:12s}: {'OK' if ok else 'not configured'}")
    print(f"  env         : {settings.APP_ENV}")
    print(f"  port        : {settings.PORT}")
    print("=" * 60)


@app.get("/health")
def health():
    return {"status": "ok", "service": "CollabForge AI API", "version": "1.0.0"}


@app.get("/")
def root():
    return {
        "name": "CollabForge AI API",
        "tagline": "Research. Score. Create. Close.",
        "docs": "/docs",
        "health": "/health",
        "capabilities": "/api/v1/system/capabilities",
    }
