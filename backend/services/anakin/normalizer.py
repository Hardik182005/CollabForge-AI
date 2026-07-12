"""Normalize Anakin responses (Wire jobs, scraper, search) into Evidence objects."""
import re
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from models.evidence import Evidence


def _clean(text: str, limit: int = 400) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()[:limit]


def from_search(result: dict, source_label: str = "web") -> list:
    """Anakin Search API → evidence list (cited results with snippets/dates)."""
    out = []
    for r in result.get("results", []) or []:
        out.append(Evidence(
            source=source_label,
            source_type="article",
            title=_clean(r.get("title") or r.get("url") or "", 150),
            url=r.get("url") or "",
            published_at=r.get("date"),
            snippet=_clean(r.get("snippet"), 500),
            data_method="anakin_search",
            confidence="medium",
        ))
    return out


def from_scrape_json(url: str, generated: dict, source: str, source_type: str = "page") -> Evidence:
    data = generated.get("data") if isinstance(generated, dict) else {}
    return Evidence(
        source=source,
        source_type=source_type,
        title=_clean((data or {}).get("title") or (data or {}).get("name") or url, 150),
        url=url,
        snippet=_clean(str(data)[:500]),
        data_method="anakin_scrape",
        confidence="high",
    )


def parse_count(val) -> int:
    """'2.4M subscribers' / '18M+' / '1,234' / 1234 → int (0 when unknown)."""
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val or "").upper().replace(",", "").strip()
    m = re.search(r"([\d.]+)\s*([KMB])?", s)
    if not m:
        return 0
    try:
        n = float(m.group(1))
    except ValueError:
        return 0
    mult = {"K": 1e3, "M": 1e6, "B": 1e9}.get(m.group(2) or "", 1)
    return int(n * mult)
