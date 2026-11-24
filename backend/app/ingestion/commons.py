"""One compatible Wikimedia Commons photograph per destination. NC, ND and unknown licenses are rejected."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings
from app.ingestion.http import cache_file, cached_record, request_json

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
_TAG = re.compile(r"<[^>]+>")


def fetch_image(slug: str, title: str, *, refresh: bool = False) -> dict[str, Any]:
    path = cache_file("commons", slug)

    def load() -> dict[str, Any]:
        filename = _page_image(title)
        if not filename:
            return {"slug": slug, "status": "no_page_image", "source_type": "commons"}
        payload = request_json(
            COMMONS_API,
            params={
                "action": "query",
                "titles": filename if filename.startswith("File:") else f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url|size|mime|extmetadata",
                "iiurlwidth": 960,
                "format": "json",
                "formatversion": 2,
            },
        )
        chosen = select_image(payload)
        if chosen is None:
            return {"slug": slug, "status": "no_compatible_license", "page_image": filename, "source_type": "commons"}
        local = _download(slug, chosen)
        if local is None:
            return {"slug": slug, "status": "download_failed", "source_type": "commons", **chosen}
        return {"slug": slug, "status": "ok", "source_type": "commons", "local_path": local, **chosen}

    return cached_record(path, refresh=refresh, loader=load)


def _page_image(title: str) -> str:
    payload = request_json(
        WIKIPEDIA_API,
        params={
            "action": "query",
            "titles": title,
            "redirects": 1,
            "prop": "pageimages",
            "piprop": "name",
            "format": "json",
            "formatversion": 2,
        },
    )
    pages = (payload.get("query") or {}).get("pages") or []
    if not isinstance(pages, list) or not pages or not isinstance(pages[0], dict):
        return ""
    return str(pages[0].get("pageimage") or "")


def select_image(payload: dict[str, Any]) -> dict[str, Any] | None:
    pages = (payload.get("query") or {}).get("pages") or []
    if not isinstance(pages, list):
        return None
    for page in pages:
        if not isinstance(page, dict):
            continue
        info = (page.get("imageinfo") or [None])[0]
        if not isinstance(info, dict):
            continue
        meta = info.get("extmetadata") or {}
        license_name = _meta(meta, "LicenseShortName")
        if not license_allowed(license_name):
            continue
        url = info.get("thumburl") or ""
        if not str(url).startswith("https://"):
            continue
        author = _plain(_meta(meta, "Artist"))[:240]
        description = _plain(_meta(meta, "ImageDescription"))[:240]
        return {
            "title": page.get("title") or "",
            "source_url": info.get("descriptionurl") or "",
            "file_url": url,
            "license_name": license_name,
            "license_url": _meta(meta, "LicenseUrl"),
            "author": author,
            "width": info.get("thumbwidth") or info.get("width"),
            "height": info.get("thumbheight") or info.get("height"),
            "mime": info.get("mime") or "",
            "alt": description or str(page.get("title") or ""),
            "attribution": _attribution(author, license_name, info.get("descriptionurl") or ""),
        }
    return None


def license_allowed(name: str) -> bool:
    text = (name or "").strip().lower()
    if not text:
        return False
    if any(token in text for token in ("nc", "noncommercial", "non-commercial", "nd", "noderiv", "no derivatives", "fair use")):
        return False
    if text in {"cc0", "pd", "public domain"} or "public domain" in text or text.startswith("cc0"):
        return True
    if text.startswith("cc by-sa") or text.startswith("cc by"):
        return True
    return False


def _download(slug: str, chosen: dict[str, Any]) -> str | None:
    settings = get_settings()
    directory = settings.knowledge_root / "assets" / slug
    directory.mkdir(parents=True, exist_ok=True)
    suffix = ".jpg"
    mime = str(chosen.get("mime") or "")
    if "png" in mime:
        suffix = ".png"
    elif "webp" in mime:
        suffix = ".webp"
    target = directory / f"hero{suffix}"
    try:
        response = httpx.get(
            chosen["file_url"],
            headers={"User-Agent": settings.http_user_agent},
            timeout=30.0,
            follow_redirects=True,
        )
        response.raise_for_status()
        content = response.content
        if not content or len(content) > 4_000_000:
            return None
        target.write_bytes(content)
    except (httpx.HTTPError, OSError):
        return None
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    chosen["content_hash"] = digest
    relative = Path("assets") / slug / target.name
    return relative.as_posix()


def _meta(meta: dict[str, Any], key: str) -> str:
    raw = meta.get(key) or {}
    if isinstance(raw, dict):
        return str(raw.get("value") or "")
    return str(raw or "")


def _plain(value: str) -> str:
    return " ".join(_TAG.sub(" ", value).split())


def _attribution(author: str, license_name: str, source_url: str) -> str:
    who = author or "a Wikimedia Commons contributor"
    return f"Photo by {who}. {license_name}. {source_url}".strip()
