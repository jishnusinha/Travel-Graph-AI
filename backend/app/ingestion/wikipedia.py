"""English Wikipedia lead extracts. Missing and disambiguation pages are recorded, not replaced."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app.ingestion.http import cache_file, cached_record, request_json

API = "https://en.wikipedia.org/w/api.php"
LICENSE = "CC BY-SA 4.0"


def fetch_page(title: str, *, refresh: bool = False) -> dict[str, Any]:
    path = cache_file("wikipedia", title)

    def load() -> dict[str, Any]:
        payload = request_json(
            API,
            params={
                "action": "query",
                "prop": "extracts|revisions|info|coordinates|pageprops",
                "exintro": 1,
                "explaintext": 1,
                "exsectionformat": "plain",
                "inprop": "url",
                "rvprop": "ids|timestamp",
                "ppprop": "wikibase_item|disambiguation",
                "colimit": 1,
                "titles": title,
                "redirects": 1,
                "format": "json",
                "formatversion": 2,
            },
        )
        record = normalize_page(title, payload)
        record["adapter"] = "wikipedia-intro-v1"
        return record

    return cached_record(path, refresh=refresh, loader=load)


def normalize_page(requested: str, payload: dict[str, Any]) -> dict[str, Any]:
    query = payload.get("query") or {}
    pages = query.get("pages") or []
    if not isinstance(pages, list) or not pages:
        return {"title": requested, "requested_title": requested, "status": "malformed", "content": "", "source_type": "wikipedia"}
    page = pages[0]
    if not isinstance(page, dict):
        return {"title": requested, "requested_title": requested, "status": "malformed", "content": "", "source_type": "wikipedia"}
    if page.get("missing"):
        return {"title": requested, "requested_title": requested, "status": "missing", "content": "", "source_type": "wikipedia"}
    props = page.get("pageprops") or {}
    if "disambiguation" in props or str(page.get("title") or "").endswith("(disambiguation)"):
        return {
            "title": page.get("title") or requested,
            "requested_title": requested,
            "status": "disambiguation",
            "content": "",
            "source_type": "wikipedia",
        }
    revision = (page.get("revisions") or [{}])[0]
    if not isinstance(revision, dict):
        revision = {}
    revision_id = str(revision.get("revid") or "")
    title = page.get("title") or requested
    coords = page.get("coordinates") or []
    lat = lon = None
    if isinstance(coords, list) and coords and isinstance(coords[0], dict):
        raw_lat, raw_lon = coords[0].get("lat"), coords[0].get("lon")
        if _valid_coord(raw_lat, raw_lon):
            lat, lon = float(raw_lat), float(raw_lon)
    slug_title = title.replace(" ", "_")
    return {
        "title": title,
        "requested_title": requested,
        "status": "ok",
        "page_id": str(page.get("pageid") or ""),
        "revision_id": revision_id,
        "fetched_revision_timestamp": revision.get("timestamp"),
        "wikidata_qid": props.get("wikibase_item") or "",
        "lat": lat,
        "lon": lon,
        "coordinate_status": "wikipedia_page" if lat is not None else "unknown",
        "canonical_url": page.get("fullurl") or f"https://en.wikipedia.org/wiki/{quote(slug_title)}",
        "permalink": (
            f"https://en.wikipedia.org/w/index.php?title={quote(slug_title)}&oldid={revision_id}" if revision_id else ""
        ),
        "redirected": bool(query.get("redirects")),
        "content": page.get("extract") or "",
        "license_name": LICENSE,
        "credit": "Text from Wikipedia contributors, CC BY-SA 4.0.",
        "source_type": "wikipedia",
    }


def _valid_coord(lat: Any, lon: Any) -> bool:
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return -90 <= lat_f <= 90 and -180 <= lon_f <= 180
