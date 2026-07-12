# CollabForge AI

**Research. Score. Create. Close.**

A two-sided platform for the creator economy, built on **Anakin Wire** and the **Anakin Universal Scraper**:

- **Creator Studio** — creators research live trends and generate scripts, hooks, social content packs and real ElevenLabs voiceovers.
- **Brand Deal Desk** — businesses research creators with evidence-backed dossiers, measure fit with an explainable score, and generate the full collaboration package: outreach drafts, campaign brief, contract template and ROI scenario.
- **Collab Autopilot** — a streamed 10-stage workflow from business brief to Campaign Launch Pack.

## The problem

Brands picking influencers today rely on gut feel, stale databases and vanity metrics. Creators guess at trends. Both sides waste weeks on research, outreach and paperwork that follows the same pattern every time.

## The solution

CollabForge AI grounds every step in **live public evidence**:

1. **Business DNA** — the brand's public website is scraped (Anakin Universal Scraper with browser mode + AI JSON extraction) into an editable profile.
2. **Creator Deep Research** — a creator name becomes a dossier: real recent videos with views, engagement signals, public sentiment from news/Reddit/web, and visible sponsor history — each fact carrying an evidence link.
3. **Explainable Fit Score** — 25% relevance, 20% engagement, 15% consistency, 15% brand safety, 15% sponsor compatibility, 10% budget fit. Missing data lowers confidence; it is never replaced with invented values.
4. **Deal Documents** — personalized outreach (never auto-sent), campaign brief, and an editable contract template (with a clear not-legal-advice notice).
5. **ROI Scenario** — a simulator with fully editable assumptions, not a "predicted revenue" claim.

## Why Anakin is essential

| Need | Anakin product | How it's used |
|---|---|---|
| YouTube channel + recent videos without official API quota | **Wire** (`yt_search`, `yt_channel`, `yt_video`, `yt_comments`) when live; **Universal Scraper** (browser mode + `generateJson`) as tested fallback | Creator resolver & content intelligence |
| News & community sentiment | **Wire** (`gn_search`, `rt_search`) / **Search API** | Reputation radar |
| Business website understanding | **Universal Scraper** (AI JSON extraction) | Business DNA |
| Topic research with citations | **Search API** (`POST /v1/search`) | Trend radar, sponsor history, creator discovery |

The backend calls the **hosted Anakin REST API** (`https://api.anakin.io/v1`) with a server-side `ANAKIN_API_KEY`. MCP was used only for development-time discovery; the deployed system has **no MCP dependency**. Verified Wire action IDs (never invented) live in `backend/data/anakin_actions.json` — see `docs/ANAKIN_CAPABILITY_MATRIX.md`.

A runtime **capability registry** (`GET /api/v1/system/capabilities`) probes what is actually live and the UI only shows enabled features. Platforms without a reliable source (Instagram, TikTok, X) are explicitly disabled — never faked.

## Architecture

```
CloudFront (HTTPS, OAC) ── private S3          static frontend (vanilla JS)
        │
AWS App Runner (FastAPI container from ECR)    backend
        ├── Anakin REST (Wire / Scraper / Search)  server-side key
        ├── OpenAI (reasoning + images) · ElevenLabs (voice)
        └── DynamoDB (campaign rooms) · S3 (media)
```

Details: `docs/ARCHITECTURE.md`. Deployment: `docs/AWS_DEPLOYMENT.md`.

## Data-source truth model

Every research fact is an evidence object with `source`, `url`, `retrieved_at`, `data_method` (`anakin_wire` | `anakin_scrape` | `anakin_search` | `heuristic` | `llm_over_evidence`) and `confidence`. The UI labels facts **LIVE / ESTIMATED / UNAVAILABLE**. There is **no synthetic fallback anywhere** — failed sources produce explicit partial results.

## Local setup

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # fill ANAKIN_API_KEY, OPENAI_API_KEY (+ optional ELEVENLABS_API_KEY)
uvicorn main:app --port 8001

# frontend (separate terminal)
cd frontend
python -m http.server 3000
# open http://localhost:3000
```

## Environment variables

See `backend/.env.example`. Required in production: `ANAKIN_API_KEY`, `OPENAI_API_KEY`. Everything else is optional — a missing optional provider disables only its capability.

## AWS deployment

```bash
bash scripts/deploy_backend_aws.sh                     # ECR + App Runner + DynamoDB + media S3
BACKEND_URL=https://<apprunner-url> bash scripts/deploy_frontend_aws.sh   # S3 + CloudFront (OAC)
```

PowerShell wrappers: `scripts/deploy_backend_aws.ps1`, `scripts/deploy_frontend_aws.ps1`. No Firebase/GCP dependency remains (historical configs moved to `legacy/gcp/`).

## API

Interactive docs at `/docs`. Key routes:

```
GET  /health
GET  /api/v1/system/capabilities
POST /api/v1/business/analyze
POST /api/v1/creators/{discover|research|compare|reputation|sponsor-history|rate-estimate}
POST /api/v1/campaigns/{roi-scenario|brief|outreach|contract}
GET/POST/PUT /api/v1/campaigns[/{id}]
POST /api/v1/autopilot/run                (SSE)
POST /api/v1/trends/discover · /api/v1/content/* · /api/v1/virality/*   (Creator Studio)
```

## Testing

```bash
cd backend && python -m pytest tests -q     # 37 tests
```

Results: `docs/TEST_REPORT.md`.

## Demo

See `docs/DEMO_SCRIPT.md` — the primary flow researches **Technical Guruji** live for an Indian electronics brand with a ₹150,000 budget. Nothing about the creator is hardcoded.

## Limitations

See `docs/LIMITATIONS.md`. Highlights: YouTube-only creator research (other platforms lack a reliable source and are disabled, not faked); Wire execution was degraded server-side at build time, so the tested scraper path is the active default; rate estimates are benchmark-based ranges, not quotations.

## Responsible use

CollabForge analyzes **publicly available information only**. Sentiment findings are labelled *public sentiment signals*, not facts. No sensitive demographic attributes are inferred. Outreach is drafted, never sent automatically. Contracts are AI-generated templates requiring counsel review.

## Team

Built for the Anakin Hackathon 2026.
