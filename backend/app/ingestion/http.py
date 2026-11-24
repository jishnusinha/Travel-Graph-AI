"""Cached HTTP JSON for source adapters. Failures stay in the returned record; nothing is invented."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from app.config import get_settings


def cache_file(source: str, name: str) -> Path:
    root = get_settings().knowledge_root / "raw" / source
    root.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch if ch.isalnum() else "_" for ch in name)[:80]
    return root / f"{safe}.json"


def read_cache(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_cache(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record


def request_json(url: str, *, params: dict[str, Any] | None = None, timeout: float = 25.0, attempts: int = 3) -> dict[str, Any]:
    settings = get_settings()
    headers = {"User-Agent": settings.http_user_agent, "Accept": "application/json"}
    last_error = "request failed"
    for attempt in range(max(1, attempts)):
        try:
            response = httpx.get(url, params=params, headers=headers, timeout=timeout, follow_redirects=True)
            if response.status_code == 429:
                wait = response.headers.get("Retry-After")
                time.sleep(float(wait) if wait and wait.isdigit() else 1.5 * (attempt + 1))
                last_error = "rate_limited"
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("response was not a JSON object")
            return payload
        except httpx.TimeoutException:
            last_error = "timeout"
            time.sleep(0.4 * (attempt + 1))
        except (httpx.HTTPError, ValueError) as exc:
            last_error = str(exc) or exc.__class__.__name__
            time.sleep(0.4 * (attempt + 1))
    raise RuntimeError(last_error)


def cached_record(path: Path, *, refresh: bool, loader: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    if not refresh:
        cached = read_cache(path)
        if cached is not None:
            return cached
    try:
        record = loader()
    except RuntimeError as exc:
        record = {"status": "error", "error": str(exc)}
    return write_cache(path, record)
