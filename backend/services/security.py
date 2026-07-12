"""URL validation / SSRF protection and a light per-IP rate limiter."""
import ipaddress
import socket
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

from fastapi import HTTPException, Request

_BLOCKED_HOSTS = {"localhost", "metadata.google.internal", "169.254.169.254"}


def validate_public_url(raw: str) -> str:
    """Validate a user-submitted URL: http(s) only, public hosts only.
    Raises HTTPException(400) on anything unsafe. Returns the normalized URL."""
    raw = (raw or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="URL is required")
    if "://" not in raw:
        raw = "https://" + raw
    try:
        parsed = urlparse(raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid URL")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only http(s) URLs are allowed")
    host = (parsed.hostname or "").lower()
    if not host or host in _BLOCKED_HOSTS:
        raise HTTPException(status_code=400, detail="URL host not allowed")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="URL host could not be resolved")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified
        ):
            raise HTTPException(status_code=400, detail="URL resolves to a non-public address")
    if len(raw) > 2000:
        raise HTTPException(status_code=400, detail="URL too long")
    return raw


class RateLimiter:
    """Sliding-window in-memory limiter, keyed by client IP."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max = max_requests
        self.window = window_seconds
        self.hits = defaultdict(deque)

    def check(self, request: Request):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        q = self.hits[ip]
        while q and q[0] < now - self.window:
            q.popleft()
        if len(q) >= self.max:
            raise HTTPException(status_code=429, detail="Rate limit exceeded — try again shortly")
        q.append(now)


research_limiter = RateLimiter(max_requests=10, window_seconds=60)
generation_limiter = RateLimiter(max_requests=20, window_seconds=60)


def mask_secret(value: str) -> str:
    if not value:
        return ""
    return value[:4] + "…" + value[-4:] if len(value) > 12 else "***"
