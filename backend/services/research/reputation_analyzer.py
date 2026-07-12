"""Public sentiment signals for a creator, from Anakin-backed public sources.

Findings are 'public sentiment signals', never proven facts. Neutral,
non-defamatory language is enforced in the LLM prompt; every theme is tied
to evidence links.
"""
import asyncio
import json
import logging

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.anakin.client import anakin_client, AnakinError
from services.anakin import capability_registry
from services.anakin.normalizer import from_search
from services.ai_providers.openai_client import OpenAIChatClient
from models.evidence import Evidence, dedupe_evidence

logger = logging.getLogger("research")


async def collect_reputation_evidence(creator_name: str) -> list:
    """Gather public discussion evidence from news, Reddit, and web search."""
    tasks = [
        _news(creator_name),
        _reddit(creator_name),
        _web(creator_name),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    evidence: list = []
    for r in results:
        if isinstance(r, list):
            evidence.extend(r)
    return dedupe_evidence(evidence)[:25]


async def _news(name: str) -> list:
    if await capability_registry.wire_is_live():
        try:
            job = await anakin_client.wire_task("gn_search", {"query": name, "limit": 10})
            payload = job.get("result") or job.get("data") or {}
            arts = payload.get("articles") or payload.get("results") or []
            return [Evidence(
                source="google_news", source_type="article",
                title=a.get("title", "")[:150], url=a.get("url", ""),
                published_at=a.get("published") or a.get("date"),
                snippet=(a.get("snippet") or a.get("description") or "")[:400],
                author=a.get("source") or "", data_method="anakin_wire", confidence="high",
            ) for a in arts[:10]]
        except AnakinError:
            pass
    try:
        res = await anakin_client.search(f"Recent news coverage about the creator {name}")
        return from_search(res, "google_news")
    except AnakinError:
        return []


async def _reddit(name: str) -> list:
    if await capability_registry.wire_is_live():
        try:
            job = await anakin_client.wire_task("rt_search", {"query": name, "limit": 10, "sort": "relevance"})
            payload = job.get("result") or job.get("data") or {}
            posts = payload.get("posts") or payload.get("results") or []
            return [Evidence(
                source="reddit", source_type="post",
                title=p.get("title", "")[:150], url=p.get("url") or p.get("permalink", ""),
                published_at=p.get("created") or p.get("created_at"),
                snippet=(p.get("selftext") or p.get("text") or "")[:400],
                author=p.get("subreddit") or "",
                metrics={"score": p.get("score"), "comments": p.get("num_comments")},
                data_method="anakin_wire", confidence="high",
            ) for p in posts[:10]]
        except AnakinError:
            pass
    try:
        res = await anakin_client.search(f"What do people on Reddit and forums say about {name} (YouTube creator)? Include praise and criticism.")
        return from_search(res, "reddit")
    except AnakinError:
        return []


async def _web(name: str) -> list:
    try:
        res = await anakin_client.search(
            f"Public reputation of {name}: controversies, audience opinions, praise and complaints"
        )
        return from_search(res, "web")
    except AnakinError:
        return []


async def analyze_reputation(creator_name: str) -> dict:
    evidence = await collect_reputation_evidence(creator_name)
    if len(evidence) < 3:
        return {
            "status": "insufficient_evidence",
            "message": "Not enough public sources were found to report sentiment signals.",
            "sources_reviewed": len(evidence),
            "evidence": [e.model_dump() for e in evidence],
        }

    corpus = "\n".join(
        f"- [{e.source}] {e.title} ({e.published_at or 'date unknown'}): {e.snippet}"
        for e in evidence
    )[:9000]
    system = (
        "You analyze PUBLIC SENTIMENT SIGNALS about a creator from provided evidence only. "
        "Use neutral, non-defamatory language. Present findings as observed public sentiment, "
        "never as proven facts. If evidence is thin for a category, return an empty list for it. "
        "Never invent events, dates, or quotes. Return ONLY valid JSON."
    )
    user = (
        f"Creator: {creator_name}\nEvidence ({len(evidence)} public sources):\n{corpus}\n\n"
        'Return JSON: {"positive_themes": [..], "negative_themes": [..], '
        '"common_praise": [..], "common_complaints": [..], '
        '"risk_timeline": [{"period": "...", "signal": "...", "severity": "low|medium|high"}], '
        '"representative_snippets": [{"text": "short quote/paraphrase", "source_index": int}], '
        '"overall_tone": "positive|mixed|negative", "confidence": "high|medium|low"}'
    )
    raw = await OpenAIChatClient().complete(system, user, max_tokens=900)
    analysis = _safe_json(raw)
    if not analysis:
        return {
            "status": "partial",
            "message": "Evidence was collected but analysis generation failed.",
            "sources_reviewed": len(evidence),
            "evidence": [e.model_dump() for e in evidence],
        }
    # Map source_index snippets to URLs so every claim links to evidence.
    for s in analysis.get("representative_snippets", []) or []:
        idx = s.get("source_index")
        if isinstance(idx, int) and 0 <= idx < len(evidence):
            s["url"] = evidence[idx].url
            s["source"] = evidence[idx].source
    return {
        "status": "ok",
        "label": "Public sentiment signals — observed in public sources, not verified facts",
        "sources_reviewed": len(evidence),
        **analysis,
        "evidence": [e.model_dump() for e in evidence],
    }


def _safe_json(raw: str) -> dict:
    import re
    try:
        m = re.search(r"\{.*\}", raw or "", re.DOTALL)
        return json.loads(m.group()) if m else {}
    except (json.JSONDecodeError, AttributeError):
        return {}
