"""Standard evidence object — every research fact must be traceable to one."""
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel


class Evidence(BaseModel):
    source: str                      # youtube | reddit | google_news | web | ...
    source_type: str = "page"        # video | post | article | profile | page | comment
    title: str = ""
    url: str = ""
    published_at: Optional[str] = None
    retrieved_at: str = ""
    snippet: str = ""
    author: str = ""
    metrics: dict = {}
    data_method: str = "anakin_scrape"   # anakin_wire | anakin_scrape | anakin_search | provider_api | heuristic
    confidence: str = "medium"           # high | medium | low

    def model_post_init(self, __context):
        if not self.retrieved_at:
            self.retrieved_at = datetime.now(timezone.utc).isoformat()


def dedupe_evidence(items: list) -> list:
    """Dedupe by URL (or title when URL missing), preserving order."""
    seen, out = set(), []
    for e in items:
        key = (e.url or e.title or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out
