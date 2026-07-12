"""CollabForge AI backend tests — run with `pytest backend/tests -q`.

External network calls are mocked; these tests exercise validation, scoring
math, error handling, normalization and repository behaviour.
"""
import asyncio
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main  # noqa: E402
from services.scoring.creator_fit import compute_fit  # noqa: E402
from services.scoring.rate_estimator import estimate_rate  # noqa: E402
from services.scoring.roi_scenarios import roi_scenario  # noqa: E402
from services.anakin.normalizer import parse_count, from_search  # noqa: E402
from services.anakin.client import AnakinClient, AnakinError  # noqa: E402
from services.persistence.repository import LocalRepository  # noqa: E402
from services.generation.contract_generator import REQUIRED_SECTIONS  # noqa: E402
from models.evidence import Evidence, dedupe_evidence  # noqa: E402

client = TestClient(main.app)


# ── Health & capabilities ────────────────────────────────────────────

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert "CollabForge" in r.json()["service"]


def test_capabilities_shape():
    r = client.get("/api/v1/system/capabilities")
    assert r.status_code == 200
    body = r.json()
    # Standard envelope (spec §26)
    assert body["success"] is True
    data = body["data"]
    # spec §10 provider blocks
    assert set(data) >= {"anakin", "openai", "elevenlabs", "ffmpeg", "sources", "features"}
    assert "available" in data["anakin"]
    assert "available" in data["anakin"]["wire"]
    assert "verifiedActions" in data["anakin"]["wire"]
    assert "available" in data["anakin"]["scraper"]
    assert "available" in data["anakin"]["search"]
    for name in ("openai", "elevenlabs", "ffmpeg"):
        assert "available" in data[name]
        if not data[name]["available"]:
            assert "reason" in data[name]  # disabled providers must say why
    # richer gating retained
    assert "youtube" in data["sources"]
    for src in data["sources"].values():
        assert "enabled" in src


def test_pipeline_preview_empty_query_fails_cleanly():
    r = client.post("/api/v1/pipeline/preview", json={"query": ""})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is False
    assert body["error"]["code"] in ("EMPTY_QUERY", "ANAKIN_UNAVAILABLE", "FAILED")


def test_pipeline_stream_is_event_stream():
    with client.stream("POST", "/api/v1/pipeline/preview/stream", json={"query": ""}) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers["content-type"]
        first = next(r.iter_lines())
        assert first.startswith("data:")


# ── Business URL validation (SSRF) ───────────────────────────────────

@pytest.mark.parametrize("bad", [
    "http://localhost/admin",
    "http://127.0.0.1:8080",
    "http://169.254.169.254/latest/meta-data",
    "ftp://example.com",
    "http://10.0.0.1/x",
])
def test_business_url_ssrf_blocked(bad):
    r = client.post("/api/v1/business/analyze", json={"website": bad})
    assert r.status_code == 400


def test_business_url_required():
    r = client.post("/api/v1/business/analyze", json={"website": ""})
    assert r.status_code in (400, 422)


# ── Anakin normalization ─────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("23.7M", 23_700_000), ("79K views", 79_000), ("1,234", 1234),
    (5000, 5000), ("2.5B", 2_500_000_000), (None, 0), ("", 0),
])
def test_parse_count(raw, expected):
    assert parse_count(raw) == expected


def test_from_search_normalization():
    ev = from_search({"results": [
        {"title": "T", "url": "https://a.example", "date": "2026-01-01", "snippet": "s"},
        {"url": "https://b.example", "snippet": "no title"},
    ]}, "web")
    assert len(ev) == 2
    assert ev[0].data_method == "anakin_search"
    assert ev[0].published_at == "2026-01-01"
    assert ev[1].title  # falls back to URL


def test_evidence_dedupe():
    a = Evidence(source="web", url="https://x.example", title="A")
    b = Evidence(source="web", url="https://x.example", title="B")
    c = Evidence(source="web", url="https://y.example", title="C")
    assert len(dedupe_evidence([a, b, c])) == 2


# ── Anakin client error handling ─────────────────────────────────────

class _FakeResponse:
    def __init__(self, status_code, body=None, headers=None):
        self.status_code = status_code
        self._body = body or {}
        self.headers = headers or {}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


def _client_with_responses(monkeypatch, responses):
    c = AnakinClient()
    calls = {"n": 0}

    class FakeAsyncClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def request(self, *a, **k):
            r = responses[min(calls["n"], len(responses) - 1)]
            calls["n"] += 1
            return r

    import services.anakin.client as mod
    monkeypatch.setattr(mod.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(mod.settings, "ANAKIN_API_KEY", "test-key")
    return c, calls


def test_anakin_401(monkeypatch):
    c, _ = _client_with_responses(monkeypatch, [_FakeResponse(401)])
    with pytest.raises(AnakinError) as e:
        asyncio.run(c.search("x", cache=False))
    assert e.value.code == "AUTH"


def test_anakin_402_credit_exhaustion(monkeypatch):
    c, _ = _client_with_responses(monkeypatch, [_FakeResponse(402)])
    with pytest.raises(AnakinError) as e:
        asyncio.run(c.search("x", cache=False))
    assert e.value.code == "INSUFFICIENT_CREDITS"


def test_anakin_429_retries_then_fails(monkeypatch):
    c, calls = _client_with_responses(monkeypatch, [_FakeResponse(429, headers={"Retry-After": "0"})])
    with pytest.raises(AnakinError):
        asyncio.run(c.search("x", cache=False))
    assert calls["n"] == 3  # retried


def test_anakin_5xx_retry_then_success(monkeypatch):
    c, calls = _client_with_responses(monkeypatch, [
        _FakeResponse(503), _FakeResponse(200, {"results": []}),
    ])
    out = asyncio.run(c.search("x", cache=False))
    assert out == {"results": []}
    assert calls["n"] == 2


def test_anakin_400_not_retried(monkeypatch):
    c, calls = _client_with_responses(monkeypatch, [
        _FakeResponse(400, {"error": {"code": "invalid_request", "message": "bad"}}),
    ])
    with pytest.raises(AnakinError):
        asyncio.run(c.search("x", cache=False))
    assert calls["n"] == 1  # invalid input must not be retried


def test_anakin_missing_key(monkeypatch):
    # The client captures its keys at construction time, so both keys must be
    # cleared BEFORE the client is built. This also guarantees the test makes no
    # live network call (available == False short-circuits _request).
    import services.anakin.client as mod
    monkeypatch.setattr(mod.settings, "ANAKIN_API_KEY", "")
    monkeypatch.setattr(mod.settings, "ANAKIN_API_KEY_2", "")
    c = AnakinClient()
    assert c.available is False
    with pytest.raises(AnakinError) as e:
        asyncio.run(c.search("x", cache=False))
    assert e.value.code == "NOT_CONFIGURED"


def test_wire_job_failure(monkeypatch):
    c, _ = _client_with_responses(monkeypatch, [
        _FakeResponse(200, {"status": "processing", "job_id": "j1"}),
        _FakeResponse(200, {"status": "failed", "error": {"code": "EXECUTION_FAILED", "message": "x"}, "credits_used": 0}),
    ])
    with pytest.raises(AnakinError) as e:
        asyncio.run(c.wire_task("yt_search", {"query": "q"}, cache=False))
    assert e.value.code == "EXECUTION_FAILED"


def test_wire_job_timeout(monkeypatch):
    import services.anakin.client as mod
    c, _ = _client_with_responses(monkeypatch, [
        _FakeResponse(200, {"status": "processing", "job_id": "j1"}),
        _FakeResponse(200, {"status": "processing"}),
    ])
    monkeypatch.setattr(mod.settings, "ANAKIN_JOB_TIMEOUT_SECONDS", 1)
    with pytest.raises(AnakinError) as e:
        asyncio.run(c.wire_task("yt_search", {"query": "q"}, cache=False))
    assert e.value.code == "JOB_TIMEOUT"


# ── Creator fit scoring ──────────────────────────────────────────────

def test_fit_full_data():
    videos = [{"views": v} for v in (100, 110, 90, 105, 95)]
    fit = compute_fit(
        relevance=90,
        engagement_inputs={"subscribers": 1000, "avg_views": 100},
        videos=videos,
        brand_safety=80, sponsor_compatibility=70, budget_fit=100,
    )
    assert 0 <= fit["score"] <= 100
    assert fit["confidence"] == "high"
    assert len(fit["components"]) == 6
    assert fit["formula"].startswith("score =")


def test_fit_missing_data_reduces_confidence():
    fit = compute_fit(
        relevance=90,
        engagement_inputs={"subscribers": 0, "avg_views": 0},
        videos=[],
        brand_safety=None, sponsor_compatibility=None, budget_fit=None,
    )
    assert fit["confidence"] == "low"
    assert len(fit["missing_data"]) == 5
    # score computed only from present components — never fabricated
    assert fit["score"] == 90


def test_fit_no_data():
    fit = compute_fit(None, {}, [], None, None, None)
    assert fit["score"] is None
    assert fit["recommendation"] == "insufficient_data"


# ── Rate estimator ───────────────────────────────────────────────────

def test_rate_estimate_transparent():
    r = estimate_rate(100_000, "integrated_segment")
    assert r["status"] == "ok"
    assert r["low"] < r["expected"] < r["high"]
    assert any("100,000" in a for a in r["assumptions"])
    assert "not a confirmed" in r["label"]


def test_rate_estimate_unavailable_without_views():
    r = estimate_rate(None)
    assert r["status"] == "unavailable"
    assert "low" not in r  # no fabricated numbers


# ── ROI scenarios ────────────────────────────────────────────────────

def test_roi_math():
    r = roi_scenario(
        estimated_impressions=100_000, engagement_rate_pct=3,
        click_through_rate_pct=1, conversion_rate_pct=2,
        average_order_value=2000, campaign_cost=150_000,
    )
    base = r["scenarios"]["base"]
    assert base["clicks"] == 1000
    assert base["conversions"] == 20
    assert base["revenue"] == 40_000
    assert r["scenarios"]["worst"]["impressions"] < base["impressions"] < r["scenarios"]["best"]["impressions"]
    # break-even: cost / (clicks * AOV) = 150000/(1000*2000) = 7.5%
    assert r["break_even_conversion_rate_pct"] == 7.5
    assert "assumptions" in r


def test_roi_endpoint_validation():
    r = client.post("/api/v1/campaigns/roi-scenario", json={
        "estimated_impressions": -5, "average_order_value": 100, "campaign_cost": 100,
    })
    assert r.status_code == 422


# ── Contract sections ────────────────────────────────────────────────

def test_contract_required_sections_list():
    assert "Usage Rights" in REQUIRED_SECTIONS
    assert "Disclosure Obligations" in REQUIRED_SECTIONS
    assert "Signatures" in REQUIRED_SECTIONS
    assert len(REQUIRED_SECTIONS) >= 20


# ── Repository ───────────────────────────────────────────────────────

def test_local_repository_crud(tmp_path):
    repo = LocalRepository(path=str(tmp_path))
    rec = repo.create({"name": "Test", "status": "draft"})
    cid = rec["campaign_id"]
    assert repo.get(cid)["name"] == "Test"
    updated = repo.update(cid, {"status": "active"})
    assert updated["status"] == "active"
    assert any(c["campaign_id"] == cid for c in repo.list())
    assert repo.get("nonexistent") is None
    assert repo.update("nonexistent", {}) is None


def test_campaigns_endpoint_crud(tmp_path, monkeypatch):
    import services.persistence.repository as mod
    monkeypatch.setattr(mod, "get_repository", lambda: LocalRepository(path=str(tmp_path)))
    import api.routes.campaigns as routes
    monkeypatch.setattr(routes, "get_repository", lambda: LocalRepository(path=str(tmp_path)))
    r = client.post("/api/v1/campaigns", json={"name": "My Campaign"})
    assert r.status_code == 200
    cid = r.json()["campaign"]["campaign_id"]
    assert client.get(f"/api/v1/campaigns/{cid}").status_code == 200
    assert client.put(f"/api/v1/campaigns/{cid}", json={"status": "won"}).json()["campaign"]["status"] == "won"
    assert client.get("/api/v1/campaigns/does-not-exist").status_code == 404


# ── Compare validation ───────────────────────────────────────────────

def test_compare_requires_two():
    r = client.post("/api/v1/creators/compare", json={"creators": ["one"]})
    assert r.status_code == 422


def test_research_requires_creator():
    r = client.post("/api/v1/creators/research", json={"creator": ""})
    assert r.status_code == 422
