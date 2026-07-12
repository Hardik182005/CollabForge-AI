"""Resolve a creator name/handle to a YouTube channel with recent content.

Source routing (deterministic):
  1. Anakin Wire (yt_search / yt_channel) when Wire execution is live
  2. Anakin URL Scraper on public YouTube pages (browser + AI JSON extraction)
  3. Explicitly unavailable — never synthetic.
"""
import json
import logging
import re
from typing import Optional
from urllib.parse import quote_plus

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from services.anakin.client import anakin_client, AnakinError
from services.anakin import capability_registry
from services.anakin.normalizer import parse_count
from models.evidence import Evidence

logger = logging.getLogger("research")

_VIDEOS_PROMPT = (
    "Extract the channel metadata (name, subscribers, channel id) and the list of "
    "recent videos with title, views and published time as shown on the page."
)

_MD_VIDEO_RE = re.compile(
    r"###\s*\[(?P<title>[^\]]+)\]\((?P<url>https://www\.youtube\.com/watch\?v=[\w-]+)\)\s*"
    r"(?:\r?\n)+(?P<meta>[^\r\n#]*views[^\r\n#]*)",
    re.IGNORECASE,
)


async def resolve_creator(query: str) -> Optional[dict]:
    """Return {channel: {...}, videos: [...], evidence: [...], data_method} or None."""
    query = (query or "").strip()
    if not query:
        return None

    if await capability_registry.wire_is_live():
        try:
            result = await _via_wire(query)
            if result:
                return result
        except AnakinError as e:
            logger.warning("wire resolve failed (%s), falling back to scraper", e.code)

    # Scraper on guessed @handle URLs — fast path, works when the creator's
    # handle equals their name without spaces.
    try:
        result = await _via_scraper(query)
        if result:
            return result
    except AnakinError as e:
        logger.warning("scraper resolve failed: %s", e.code)

    # Search discovers the creator's REAL channel URL (handles rarely equal the
    # display name — e.g. "Tech Burner" → @TechBurner, "Gaurav Chaudhary" →
    # @TechnicalGuruji). Then scrape that discovered channel.
    try:
        return await _via_search(query)
    except AnakinError as e:
        logger.warning("search resolve failed: %s", e.code)
        return None


async def _via_wire(query: str) -> Optional[dict]:
    search = await anakin_client.wire_task("yt_search", {"query": query, "limit": 10})
    payload = search.get("result") or search.get("data") or {}
    items = payload.get("results") or payload.get("videos") or payload.get("items") or []
    if not items:
        return None
    # Most frequent channel among top results is our creator.
    channels: dict = {}
    for it in items:
        cid = it.get("channel_id") or (it.get("channel") or {}).get("id")
        if cid:
            channels[cid] = channels.get(cid, 0) + 1
    if not channels:
        return None
    channel_id = max(channels, key=channels.get)
    info = await anakin_client.wire_task("yt_channel", {"channel_id": channel_id})
    ch = info.get("result") or info.get("data") or {}
    videos = [
        {
            "title": it.get("title", ""),
            "url": it.get("url") or f"https://www.youtube.com/watch?v={it.get('video_id', '')}",
            "views": parse_count(it.get("views") or it.get("view_count")),
            "published": it.get("published") or it.get("published_at") or "",
            "video_id": it.get("video_id"),
        }
        for it in items
        if (it.get("channel_id") or (it.get("channel") or {}).get("id")) == channel_id
    ]
    evidence = [Evidence(
        source="youtube", source_type="profile",
        title=ch.get("name") or query,
        url=f"https://www.youtube.com/channel/{channel_id}",
        snippet=(ch.get("description") or "")[:400],
        metrics={"subscribers": parse_count(ch.get("subscribers") or ch.get("subscriber_count"))},
        data_method="anakin_wire", confidence="high",
    )]
    return {
        "channel": {
            "name": ch.get("name") or query,
            "handle": ch.get("handle") or "",
            "channel_id": channel_id,
            "subscribers": parse_count(ch.get("subscribers") or ch.get("subscriber_count")),
            "description": (ch.get("description") or "")[:500],
            "url": f"https://www.youtube.com/channel/{channel_id}",
        },
        "videos": videos,
        "evidence": evidence,
        "data_method": "anakin_wire",
    }


def _parse_video_meta(meta: str) -> tuple:
    """'79K views • 19 hours ago' → (79000, '19 hours ago')."""
    views = 0
    published = ""
    m = re.search(r"([\d.,]+\s*[KMB]?)\s*views", meta or "", re.IGNORECASE)
    if m:
        views = parse_count(m.group(1))
    p = re.search(r"views\W+(.*)$", meta or "", re.IGNORECASE)
    if p:
        published = p.group(1).strip(" •?•")
    return views, published


async def _via_scraper(query: str, urls: Optional[list] = None) -> Optional[dict]:
    """Anakin URL Scraper on the channel's /videos page. The scraper's
    generateJson returns a generic page schema: metadata carries name /
    subscribers / channel id; the markdown carries the video list.

    When ``urls`` is given (e.g. real channel pages discovered via Search) those
    are scraped directly; otherwise handle URLs are guessed from the query."""
    handle = query.replace(" ", "")
    attempt_urls = urls or [
        f"https://www.youtube.com/@{quote_plus(handle)}/videos",
        f"https://www.youtube.com/@{quote_plus(handle.title().replace(' ', ''))}/videos",
    ]
    for attempt_url in attempt_urls:
        # Prefer the @handle carried by the URL we actually scraped.
        hm = re.search(r"/@([\w.\-]+)", attempt_url)
        url_handle = hm.group(1) if hm else handle
        try:
            res = await anakin_client.scrape(attempt_url, use_browser=True, json_prompt=_VIDEOS_PROMPT)
        except AnakinError:
            continue
        gen = res.get("generatedJson") or {}
        data = gen.get("data") if isinstance(gen, dict) else {}
        meta = (data or {}).get("metadata") or {}
        markdown = res.get("markdown") or ""

        name = meta.get("name") or (data or {}).get("title") or ""
        subs = parse_count(meta.get("subscribers"))
        if not subs:
            sm = re.search(r"([\d.,]+\s*[KMB]?)\s*subscribers", markdown, re.IGNORECASE)
            if sm:
                subs = parse_count(sm.group(1))
        channel_id = meta.get("identifier") or ""
        if not name and not markdown:
            continue

        videos = []
        # Primary: the scraper's structured sections (heading = title,
        # content = "79K views • 19 hours ago").
        for sec in (data or {}).get("sections") or []:
            content = str(sec.get("content") or "")
            title = str(sec.get("heading") or "").strip()
            if not title or "views" not in content.lower():
                continue
            views, published = _parse_video_meta(content)
            url = ""
            um = re.search(
                r"\[" + re.escape(title[:40]) + r"[^\]]*\]\((https://www\.youtube\.com/watch\?v=[\w-]+)\)",
                markdown,
            )
            if um:
                url = um.group(1)
            videos.append({
                "title": title[:150], "url": url, "views": views,
                "published": published,
                "video_id": url.split("v=")[-1] if url else None,
            })
            if len(videos) >= 12:
                break
        # Fallback: parse the markdown directly.
        if not videos:
            for m in _MD_VIDEO_RE.finditer(markdown):
                views, published = _parse_video_meta(m.group("meta"))
                videos.append({
                    "title": m.group("title").strip()[:150],
                    "url": m.group("url"),
                    "views": views,
                    "published": published,
                    "video_id": m.group("url").split("v=")[-1],
                })
                if len(videos) >= 12:
                    break
        if not videos and not subs:
            continue

        # Sanity check: the channel we found should resemble the query.
        # Space-insensitive so "TechBurner" matches the channel "Tech Burner".
        qtokens = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
        qnorm = re.sub(r"\W+", "", query.lower())
        nnorm = re.sub(r"\W+", "", (name or "").lower())
        token_hit = any(t in name.lower() for t in qtokens)
        norm_hit = bool(qnorm) and bool(nnorm) and (qnorm in nnorm or nnorm in qnorm)
        if name and qtokens and not token_hit and not norm_hit:
            continue

        channel_url = meta.get("url") or attempt_url.rsplit("/videos", 1)[0]
        description = ""
        dm = re.search(r"^#\s+.*?\n\n(.+?)\n\n", markdown, re.DOTALL)
        if dm:
            description = re.sub(r"\s+", " ", dm.group(1))[:500]

        evidence = [Evidence(
            source="youtube", source_type="profile",
            title=name or query, url=channel_url,
            snippet=description[:400],
            metrics={"subscribers": subs, "recent_videos_observed": len(videos)},
            data_method="anakin_scrape", confidence="high" if subs else "medium",
        )]
        return {
            "channel": {
                "name": name or query,
                "handle": f"@{url_handle}",
                "channel_id": channel_id or None,
                "subscribers": subs,
                "description": description,
                "url": channel_url,
            },
            "videos": videos,
            "evidence": evidence,
            "data_method": "anakin_scrape",
        }
    return None


def _youtube_videos_url(url: str) -> Optional[str]:
    """Normalize any YouTube channel URL to its /videos page. Returns None for
    non-channel URLs (search, watch, shorts, playlists)."""
    if not url or "youtube.com" not in url and "youtu.be" not in url:
        return None
    m = re.search(r"youtube\.com/(@[\w.\-]+|channel/[\w\-]+|c/[\w.\-]+|user/[\w.\-]+)", url)
    if not m:
        return None
    base = f"https://www.youtube.com/{m.group(1)}"
    return f"{base}/videos"


async def _via_search(query: str) -> Optional[dict]:
    """Discover the creator's real channel via Anakin Search, then scrape it.
    Robust to handles that differ from the display name."""
    res = await anakin_client.search(f"{query} official YouTube channel")
    seen: list = []
    for r in (res.get("results") or []):
        vu = _youtube_videos_url(r.get("url") or "")
        if vu and vu not in seen:
            seen.append(vu)
    if not seen:
        return None
    # Scrape the top few discovered channel pages; first solid match wins.
    return await _via_scraper(query, urls=seen[:3])
