"""Wikivoyage extract adapter. Caches responses and records redirects and missing pages."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from app.config import get_settings


class WikivoyageError(RuntimeError):
    pass


_LISTING = re.compile(r"^(?:\d+\s+)?([A-Z][^—–\n]{2,70}?)\s+(?:—|–)\s+")
_MENTIONED = re.compile(
    r"\b([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){0,3}\s(?:Falls|Beach|Temple|Lake|Fort|Park|Museum|Peak|Waterfall))\b"
)


def lead_excerpt(text: str, *, limit: int = 320) -> str:
    """First paragraph of a plaintext extract, cut on a sentence when it is long."""
    body = (text or "").strip()
    cut = body.find("\n\n")
    lead = body if cut < 40 else body[:cut]
    lead = " ".join(lead.split())
    if len(lead) <= limit:
        return lead
    stop = lead.rfind(". ", 0, limit)
    if stop >= 80:
        return lead[: stop + 1]
    return lead[:limit].rstrip() + "…"


def listing_names(text: str, *, limit: int = 12) -> list[str]:
    """Names that Wikivoyage plaintext marks with an em dash. No coordinates are inferred."""
    found: list[str] = []
    for line in (text or "").splitlines():
        match = _LISTING.match(line.strip())
        if not match:
            continue
        name = match.group(1).strip(" .")
        if name and name not in found:
            found.append(name)
        if len(found) >= limit:
            break
    return found


def mentioned_place_names(text: str, *, limit: int = 8) -> list[str]:
    """Proper names that occur in the extract. Coordinates are not inferred."""
    found: list[str] = []
    for match in _MENTIONED.finditer(text or ""):
        name = match.group(1)
        if name not in found:
            found.append(name)
        if len(found) >= limit:
            break
    return found


def cache_path(title: str) -> Path:
    root = get_settings().knowledge_root / "raw" / "wikivoyage"
    root.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() else "_" for ch in title)[:80]
    return root / f"{safe}.json"


def fetch_extract(title: str, *, refresh: bool = False, timeout: float = 20.0) -> dict[str, Any]:
    path = cache_path(title)
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    settings = get_settings()
    params = {
        "action": "query",
        "prop": "extracts|revisions|info",
        "explaintext": 1,
        "exsectionformat": "plain",
        "inprop": "url",
        "rvprop": "ids|timestamp",
        "titles": title,
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
    }
    last_error = "request failed"
    for attempt in range(3):
        try:
            response = httpx.get(
                "https://en.wikivoyage.org/w/api.php",
                params=params,
                headers={"User-Agent": settings.http_user_agent, "Accept": "application/json"},
                timeout=timeout,
                follow_redirects=True,
            )
            if response.status_code == 429:
                time.sleep(1.5 * (attempt + 1))
                last_error = "rate_limited"
                continue
            response.raise_for_status()
            payload = response.json()
            record = _normalize(title, payload)
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            return record
        except httpx.TimeoutException:
            last_error = "timeout"
            time.sleep(0.5 * (attempt + 1))
        except httpx.HTTPError as exc:
            last_error = str(exc)
            time.sleep(0.5 * (attempt + 1))
    return {"title": title, "status": "error", "error": last_error, "content": ""}


def _normalize(requested: str, payload: dict[str, Any]) -> dict[str, Any]:
    query = payload.get("query") or {}
    pages = query.get("pages") or []
    if not pages:
        return {"title": requested, "status": "missing", "content": ""}
    page = pages[0]
    if page.get("missing"):
        return {"title": requested, "status": "missing", "content": ""}
    redirects = query.get("redirects") or []
    revision = (page.get("revisions") or [{}])[0]
    revision_id = str(revision.get("revid") or "")
    title = page.get("title") or requested
    return {
        "title": title,
        "requested_title": requested,
        "status": "ok",
        "page_id": str(page.get("pageid") or ""),
        "revision_id": revision_id,
        "fetched_revision_timestamp": revision.get("timestamp"),
        "canonical_url": page.get("fullurl") or f"https://en.wikivoyage.org/wiki/{quote(title.replace(' ', '_'))}",
        "permalink": f"https://en.wikivoyage.org/w/index.php?title={quote(title.replace(' ', '_'))}&oldid={revision_id}" if revision_id else "",
        "redirected": bool(redirects),
        "redirects": redirects,
        "content": page.get("extract") or "",
        "license_name": "CC BY-SA 4.0",
        "credit": "Text from Wikivoyage contributors, CC BY-SA 4.0.",
        "source_type": "wikivoyage",
    }
