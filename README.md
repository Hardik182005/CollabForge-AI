<div align="center">

# 🚀 CollabForge AI

### **Research. Score. Create. Close.**

*Creator intelligence, built on live evidence — powered by Anakin Wire & the Universal Scraper.*

<br/>

[![Live App](https://img.shields.io/badge/🌐_Live_App-d2l3jsjzyhefqq.cloudfront.net-2563eb?style=for-the-badge)](https://d2l3jsjzyhefqq.cloudfront.net)
[![Status](https://img.shields.io/badge/status-LIVE-16a34a?style=for-the-badge)](https://d2l3jsjzyhefqq.cloudfront.net/health)
![Release Gate](https://img.shields.io/badge/release_gate-PASS-16a34a?style=for-the-badge)

<br/>

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?logo=fastapi&logoColor=white)
![JavaScript](https://img.shields.io/badge/Frontend-Vanilla_JS-F7DF1E?logo=javascript&logoColor=black)
![Anakin](https://img.shields.io/badge/Anakin-Wire_·_Scraper_·_Search-6d28d9)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai&logoColor=white)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-Voice-000000)
![FFmpeg](https://img.shields.io/badge/FFmpeg-Reels-007808?logo=ffmpeg&logoColor=white)

![AWS](https://img.shields.io/badge/AWS-ECS_Fargate_·_ALB_·_CloudFront-FF9900?logo=amazonaws&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ECR-2496ED?logo=docker&logoColor=white)
![DynamoDB](https://img.shields.io/badge/DynamoDB-Campaigns-4053D6?logo=amazondynamodb&logoColor=white)
![S3](https://img.shields.io/badge/S3-Media_+_Frontend-569A31?logo=amazons3&logoColor=white)
![Tests](https://img.shields.io/badge/tests-39_passed-16a34a)
![API](https://img.shields.io/badge/API_contract-37%2F37-16a34a)
![No Fake Data](https://img.shields.io/badge/synthetic_data-none-16a34a)

</div>

---

## 🔗 Live deployment

| Surface | URL |
|---|---|
| 🌐 **Web app (CloudFront)** | **https://d2l3jsjzyhefqq.cloudfront.net** |
| ❤️ Health check | https://d2l3jsjzyhefqq.cloudfront.net/health |
| 🧠 Runtime capabilities | https://d2l3jsjzyhefqq.cloudfront.net/api/v1/system/capabilities |
| 📚 Interactive API docs | https://d2l3jsjzyhefqq.cloudfront.net/docs |
| 🎬 Creator Studio | https://d2l3jsjzyhefqq.cloudfront.net/app.html?workspace=creator |
| 🏢 Brand Intelligence | https://d2l3jsjzyhefqq.cloudfront.net/app.html?workspace=brand |
| 🤖 Collab Autopilot | https://d2l3jsjzyhefqq.cloudfront.net/app.html?workspace=brand&view=autopilot |

> **Region:** `eu-west-1` · **Backend:** ECS Fargate behind an ALB, fronted same-origin by CloudFront (`/api/*` → ALB). `/health` returns `{"status":"ok"}`.

---

## 🎯 What it does

CollabForge AI is a two-sided platform for the creator economy where **every step is grounded in live public evidence** — no vanity metrics, no stale databases, no synthetic data.

| Product | For | What you get |
|---|---|---|
| 🎬 **Creator Studio** | Creators | Live trend discovery, script studio, hook lab, social content packs, real **ElevenLabs** voiceovers, AI reel/storyboard + **FFmpeg** MP4, virality heuristic |
| 🏢 **Brand Intelligence** | Brands | Evidence-backed creator dossiers, explainable fit score, comparison, ROI scenarios, outreach drafts, campaign brief, contract template, Campaign Room |
| 🤖 **Collab Autopilot** | Brands | One guided run → streamed **10-stage** pipeline → full Campaign Launch Pack, saved to the Campaign Room |

---

## 💡 The problem → the solution

Brands pick influencers on gut feel, stale databases and vanity metrics. Creators guess at trends. Both waste weeks on research, outreach and paperwork that follows the same pattern every time.

CollabForge grounds every step in **live public evidence**:

1. **Business DNA** — the brand's public website is scraped (Anakin Universal Scraper, browser mode + AI JSON extraction) into an editable profile.
2. **Creator Deep Research** — a creator name becomes a dossier: real recent videos with views, engagement signals, public sentiment from news/Reddit/web, and visible sponsor history — each fact carrying an evidence link.
3. **Explainable Fit Score** — 25% relevance · 20% engagement · 15% consistency · 15% brand safety · 15% sponsor compatibility · 10% budget fit. Missing data lowers confidence; it is **never** replaced with invented values.
4. **Deal Documents** — personalized outreach (never auto-sent), campaign brief, editable contract template (with a clear *not-legal-advice* notice).
5. **ROI Scenario** — a simulator with fully editable assumptions, not a "predicted revenue" claim.

---

## 🟣 Why Anakin is essential

| Need | Anakin product | How it's used | Live status |
|---|---|---|---|
| Business website understanding | **Universal Scraper** (AI JSON extraction) | Business DNA | ✅ live |
| Topic research with citations | **Search API** (`POST /v1/search`) | Trend radar, sponsor history, creator discovery | ✅ live |
| Creator channel + recent videos | **Universal Scraper** on public YouTube pages; **Search** discovers the real channel URL | Creator resolver | ✅ live |
| Structured YouTube/News/Reddit reads | **Wire** (`yt_*`, `gn_*`, `rt_*`) — 44 verified actions | Content intelligence when Wire is up | ⚠️ degraded upstream → auto-fallback to Scraper/Search |

The backend calls the **hosted Anakin REST API** (`https://api.anakin.io/v1`) with a server-side `ANAKIN_API_KEY`. MCP was used **only** for development-time discovery — the deployed system has **no MCP dependency**. Verified Wire action IDs (never invented) live in [`backend/data/anakin_actions.json`](backend/data/anakin_actions.json).

A runtime **capability registry** (`GET /api/v1/system/capabilities`) probes what is actually live and the UI only shows enabled features. Platforms without a reliable source (Instagram, TikTok, X) are **explicitly disabled — never faked**.

---

## 🏗️ Architecture

```
                        ┌─────────────────────────────────────────┐
   Browser ──HTTPS──►   │  CloudFront  (E1K9WW29XTY2AP)            │
                        │   ├── /            → S3 (private, OAC)   │  vanilla-JS frontend
                        │   └── /api/* /health /docs → ALB origin  │
                        └───────────────────┬─────────────────────┘
                                             │ (same-origin proxy)
                        ┌────────────────────▼─────────────────────┐
                        │  ALB  collabforge-alb  →  ECS Fargate     │
                        │  service: collabforge-backend  (FastAPI)  │  image: ECR :latest
                        │   ├── Anakin REST  (Wire / Scraper / Search)   server-side key
                        │   ├── OpenAI (reasoning + images) · ElevenLabs (voice)
                        │   ├── FFmpeg (reel MP4 composition)
                        │   └── DynamoDB (campaign rooms) · S3 (media)
                        └───────────────────────────────────────────┘
```

**AWS resources** (account `824604027501`, `eu-west-1`):

| Resource | Name / ID |
|---|---|
| CloudFront | `E1K9WW29XTY2AP` → `d2l3jsjzyhefqq.cloudfront.net` |
| Frontend S3 (private, OAC) | `collabforge-frontend-824604027501` |
| ALB | `collabforge-alb-1772822941.eu-west-1.elb.amazonaws.com` |
| ECS | cluster `collabforge` · service `collabforge-backend` (Fargate) |
| Container registry | ECR `collabforge-backend:latest` |
| Database | DynamoDB `collabforge-campaigns` |
| Media | S3 `collabforge-media-824604027501` |

> ℹ️ **App Runner is not available on this account** (`SubscriptionRequiredException`), so the backend runs on **ECS Fargate + ALB**. Deploy scripts live in [`scripts/`](scripts/).

---

## 🔒 Data-source truth model

Every research fact is an evidence object with `source`, `url`, `retrieved_at`, `data_method`
(`anakin_wire` | `anakin_scrape` | `anakin_search` | `heuristic` | `llm_over_evidence`) and
`confidence`. The UI labels facts **LIVE / ESTIMATED / UNAVAILABLE**. There is **no synthetic
fallback anywhere** — failed sources produce explicit partial results (e.g. Autopilot shows
"research failed for X" rather than inventing a dossier).

---

## ⚡ Quick start (local)

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env        # fill ANAKIN_API_KEY, OPENAI_API_KEY (+ optional ELEVENLABS_API_KEY)
uvicorn main:app --port 8001

# Frontend (separate terminal)
cd frontend
python -m http.server 3000
# open http://localhost:3000
```

Required in production: `ANAKIN_API_KEY`, `OPENAI_API_KEY`. Everything else is optional — a
missing optional provider disables only its capability. FFmpeg enables reel MP4 composition
(bundled in the Docker image). See [`backend/.env.example`](backend/.env.example).

---

## ☁️ Deploy to AWS

```bash
# Backend → Docker build → ECR → ECS Fargate rolling update (updates the existing service)
AWS_REGION=eu-west-1 FRONTEND_ORIGIN=https://d2l3jsjzyhefqq.cloudfront.net \
  bash scripts/deploy_backend_aws_ecs.sh

# Frontend → S3 sync → CloudFront invalidation (updates the existing distribution)
AWS_REGION=eu-west-1 BACKEND_URL=http://collabforge-alb-1772822941.eu-west-1.elb.amazonaws.com \
  bash scripts/deploy_frontend_aws.sh
```

PowerShell wrappers: `scripts/deploy_backend_aws.ps1`, `scripts/deploy_frontend_aws.ps1`.
Secrets are read from `backend/.env` at deploy time and injected as runtime env — never baked
into the image or printed. No Firebase/GCP runtime dependency remains (historical configs archived under `legacy/`).

---

## 🔌 API

Interactive docs at [`/docs`](https://d2l3jsjzyhefqq.cloudfront.net/docs). Key routes:

```
GET  /health
GET  /api/v1/system/capabilities
POST /api/v1/business/analyze
POST /api/v1/creators/{discover|research|compare|reputation|sponsor-history|rate-estimate}
POST /api/v1/creators/research/stream                       (SSE)
POST /api/v1/campaigns/{roi-scenario|brief|outreach|contract}
GET/POST/PUT /api/v1/campaigns[/{id}]
POST /api/v1/pipeline/preview · /api/v1/pipeline/preview/stream   (SSE)
POST /api/v1/autopilot/run                                  (SSE, 10 stages)
POST /api/v1/trends/discover · /api/v1/content/* · /api/v1/virality/*
GET  /api/v1/media/voices · POST /api/v1/media/{voice|reel}
POST /api/v1/chat/                                          (Forge assistant)
```

---

## ✅ Testing & release evidence

```bash
cd backend && python -m pytest tests -q        # 39 passed
```

| Area | Result |
|---|---|
| Backend API contract | **37/37** endpoints pass · no 500 on valid flows · SSRF/XSS/oversize → structured 4xx |
| Unit/integration | **39 passed / 0 failed** |
| Anakin live | Scraper ✅ · Search ✅ (distinct queries → distinct real URLs) · Wire ⚠️ degraded upstream (honestly reported) |
| Pipeline / SSE | `text/event-stream`, incremental, backend-driven |
| Autopilot E2E (live prod) | 10 stages, real evidence, saved to Campaign Room, honest partial-failure reporting |
| Chatbot (Forge) | `POST /api/v1/chat/` 200, accurate, non-hallucinated |
| Frontend | 0 broken-endpoint buttons · no fake data as live · no secrets in bundle · 0 console errors |
| Security | SSRF/path-traversal/XSS-escape/log-redaction all pass |

Verdict: **PASS with approved non-blocking exceptions** (Anakin Wire degraded upstream, honestly reported). Verified live against production.

---

## 🎥 Demo flow

The flagship Autopilot run researches real Indian creators (**Technical Guruji**, **Tech Burner**,
**Gaurav Chaudhary**) live for a **Croma** gaming-smartphone launch with a **₹1,50,000** budget.
Nothing about any creator is hardcoded — every fact carries an evidence link.

---

## ⚠️ Limitations

Highlights: YouTube-focused creator research
(other platforms lack a reliable source and are disabled, not faked); Anakin **Wire** execution is
degraded upstream, so the live Scraper + Search paths are the active default; rate estimates are
benchmark-based ranges, not quotations; contracts are AI-generated templates requiring counsel review.

---

## 🛡️ Responsible use

CollabForge analyzes **publicly available information only**. Sentiment findings are labelled *public
sentiment signals*, not facts. No sensitive demographic attributes are inferred. Outreach is drafted,
**never sent automatically**. Contracts are AI-generated templates requiring counsel review.

---

<div align="center">

Built for the **Anakin Hackathon 2026** · *Research. Score. Create. Close.*

</div>
