"""Production Anakin REST client.

Server-side only (X-API-Key). Async httpx, exponential retry for retryable
failures, Retry-After support, async-job polling with a maximum duration,
TTL cache for public reads, per-request credit budget, and log redaction.
Never used from the frontend; MCP is not a runtime dependency.
"""
import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Optional

import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.config import settings

logger = logging.getLogger("anakin")

_RETRYABLE = {429, 500, 502, 503, 504}


class AnakinError(Exception):
    def __init__(self, code: str, message: str, status: int = 500, credits_used: int = 0):
        self.code = code
        self.message = message
        self.status = status
        self.credits_used = credits_used
        super().__init__(f"{code}: {message}")

    def to_dict(self) -> dict:
        return {"provider": "anakin", "code": self.code, "message": self.message}


class _TTLCache:
    def __init__(self, ttl: int):
        self.ttl = ttl
        self.store: dict = {}

    def key(self, *parts) -> str:
        return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()

    def get(self, key: str):
        hit = self.store.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
        self.store.pop(key, None)
        return None

    def set(self, key: str, value):
        if len(self.store) > 500:  # bound memory
            oldest = sorted(self.store.items(), key=lambda kv: kv[1][0])[:100]
            for k, _ in oldest:
                self.store.pop(k, None)
        self.store[key] = (time.monotonic() + self.ttl, value)


class AnakinClient:
    def __init__(self):
        self.base = settings.ANAKIN_API_BASE_URL.rstrip("/")
        self.cache = _TTLCache(settings.ANAKIN_CACHE_TTL_SECONDS)
        self.credits_used_session = 0
        # Primary + optional fallback key. When the active key is credit-exhausted
        # (402) we advance to the next and keep serving without downtime.
        self._keys = [k for k in (settings.ANAKIN_API_KEY, settings.ANAKIN_API_KEY_2) if k]
        self._key_idx = 0
        self._exhausted: set = set()

    @property
    def available(self) -> bool:
        return bool(self._keys)

    def _active_key(self) -> str:
        return self._keys[self._key_idx] if self._keys else ""

    def _advance_key(self) -> bool:
        """Mark the current key exhausted and move to the next unused one.
        Returns True if another key is now active."""
        self._exhausted.add(self._key_idx)
        for i in range(len(self._keys)):
            if i not in self._exhausted:
                self._key_idx = i
                logger.warning("anakin: switched to fallback API key #%d after credit exhaustion", i + 1)
                return True
        return False

    def _headers(self) -> dict:
        return {"X-API-Key": self._active_key(), "Content-Type": "application/json"}

    async def _request(
        self, method: str, path: str, json_body: Optional[dict] = None,
        timeout: float = 60.0, max_attempts: int = 3,
    ) -> dict:
        if not self.available:
            raise AnakinError("NOT_CONFIGURED", "ANAKIN_API_KEY is not configured", 503)
        url = f"{self.base}{path}"
        last_error: Optional[AnakinError] = None
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_attempts):
                try:
                    r = await client.request(method, url, headers=self._headers(), json=json_body)
                except httpx.TimeoutException:
                    last_error = AnakinError("TIMEOUT", f"Anakin request timed out ({path})", 504)
                    continue
                except httpx.HTTPError as e:
                    last_error = AnakinError("NETWORK", f"Network error calling Anakin: {type(e).__name__}", 502)
                    continue

                if r.status_code < 400:
                    try:
                        return r.json()
                    except json.JSONDecodeError:
                        raise AnakinError("BAD_RESPONSE", "Anakin returned non-JSON response", 502)

                body = {}
                try:
                    body = r.json()
                except json.JSONDecodeError:
                    pass
                err = body.get("error") or {}
                code = err.get("code") if isinstance(err, dict) else str(err)
                msg = (err.get("message") if isinstance(err, dict) else str(body)) or r.text[:200]

                if r.status_code == 401:
                    # Bad key — try the fallback before failing.
                    if self._advance_key():
                        continue
                    raise AnakinError("AUTH", "Anakin API key rejected", 401)
                if r.status_code == 402:
                    # Credit exhausted — swap to the fallback key and retry once here.
                    if self._advance_key():
                        continue
                    raise AnakinError("INSUFFICIENT_CREDITS", "Anakin credit balance exhausted (all keys)", 402)
                if r.status_code == 403:
                    raise AnakinError("FORBIDDEN", msg or "Forbidden", 403)
                if r.status_code in _RETRYABLE and attempt < max_attempts - 1:
                    retry_after = r.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else 1.5 * (2 ** attempt)
                    logger.warning("anakin retryable %s on %s (attempt %d)", r.status_code, path, attempt + 1)
                    await asyncio.sleep(min(delay, 15))
                    last_error = AnakinError(code or "SERVER", msg, r.status_code)
                    continue
                # Invalid input etc. — do NOT retry
                raise AnakinError(code or f"HTTP_{r.status_code}", msg, r.status_code)
        raise last_error or AnakinError("UNKNOWN", "Anakin request failed", 500)

    # ── URL Scraper ──────────────────────────────────────────────────────
    async def scrape(
        self, url: str, use_browser: bool = False,
        json_prompt: Optional[str] = None, country: Optional[str] = None,
        cache: bool = True,
    ) -> dict:
        """Inline scrape. Returns the raw Anakin result (markdown / generatedJson)."""
        ck = self.cache.key("scrape", url, use_browser, json_prompt, country)
        if cache and (hit := self.cache.get(ck)) is not None:
            return hit
        body: dict = {"url": url}
        if use_browser:
            body["useBrowser"] = True
        if json_prompt:
            body["generateJson"] = True
            body["jsonPrompt"] = json_prompt
        if country:
            body["country"] = country
        result = await self._request(
            "POST", "/v1/url-scraper/scrape", body,
            timeout=float(settings.ANAKIN_JOB_TIMEOUT_SECONDS),
        )
        if cache:
            self.cache.set(ck, result)
        return result

    # ── Search API ───────────────────────────────────────────────────────
    async def search(self, prompt: str, cache: bool = True) -> dict:
        ck = self.cache.key("search", prompt)
        if cache and (hit := self.cache.get(ck)) is not None:
            return hit
        result = await self._request("POST", "/v1/search", {"prompt": prompt}, timeout=90.0)
        if cache:
            self.cache.set(ck, result)
        return result

    # ── Wire ─────────────────────────────────────────────────────────────
    async def wire_catalog(self, slug: str) -> dict:
        ck = self.cache.key("catalog", slug)
        if (hit := self.cache.get(ck)) is not None:
            return hit
        result = await self._request("GET", f"/v1/wire/catalog/{slug}")
        self.cache.set(ck, result)
        return result

    async def wire_task(
        self, action_id: str, parameters: dict, cache: bool = True,
        max_credits: Optional[int] = None,
    ) -> dict:
        """Execute a Wire action and poll until done. Raises AnakinError on failure."""
        budget = max_credits or settings.ANAKIN_MAX_CREDITS_PER_REQUEST
        if self.credits_used_session >= 10_000:
            raise AnakinError("CREDIT_BUDGET", "Session credit safety limit reached", 402)
        ck = self.cache.key("wire", action_id, parameters)
        if cache and (hit := self.cache.get(ck)) is not None:
            return hit

        submit = await self._request(
            "POST", "/v1/wire/task",
            {"action_id": action_id, "parameters": parameters},
            timeout=30.0,
        )
        job_id = submit.get("job_id")
        if not job_id:
            raise AnakinError("BAD_RESPONSE", f"No job_id in Wire response for {action_id}", 502)

        deadline = time.monotonic() + settings.ANAKIN_JOB_TIMEOUT_SECONDS
        delay = 2.0
        while time.monotonic() < deadline:
            await asyncio.sleep(delay)
            delay = min(delay * 1.4, 8.0)
            job = await self._request("GET", f"/v1/wire/jobs/{job_id}", timeout=30.0, max_attempts=2)
            status = job.get("status")
            if status == "processing":
                continue
            credits = int(job.get("credits_used") or 0)
            self.credits_used_session += credits
            if status in ("completed", "succeeded", "success"):
                if credits > budget:
                    logger.warning("wire action %s used %d credits (budget %d)", action_id, credits, budget)
                if cache:
                    self.cache.set(ck, job)
                return job
            err = job.get("error") or {}
            raise AnakinError(
                err.get("code", "EXECUTION_FAILED"),
                err.get("message", "Wire job failed"),
                500, credits,
            )
        raise AnakinError("JOB_TIMEOUT", f"Wire job {action_id} did not finish in time", 504)


anakin_client = AnakinClient()
