"""Build a snapshot from the cached Wikivoyage extracts and the destination registry.

Usage (from backend/, with the venv active):
  python -m app.ingestion.cli fetch --limit 12
  python -m app.ingestion.cli build --snapshot india-v1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.config import ROOT, get_settings
from app.ingestion.wikivoyage import fetch_extract, lead_excerpt, listing_names, mentioned_place_names
from app.rag.embeddings import get_embedder
from app.rag.store import import_corpus


def registry_path() -> Path:
    return ROOT / "data" / "knowledge" / "manifests" / "destinations.json"


def load_registry(limit: int | None) -> list[dict]:
    payload = json.loads(registry_path().read_text(encoding="utf-8"))
    rows = payload["destinations"]
    return rows[:limit] if limit else rows


def fetch(limit: int | None, refresh: bool) -> dict:
    failures = []
    ok = 0
    for dest in load_registry(limit):
        title = dest.get("wikivoyage_title") or dest["name"]
        record = fetch_extract(title, refresh=refresh)
        if record.get("status") != "ok" or not (record.get("content") or "").strip():
            failures.append({"slug": dest["slug"], "title": title, "status": record.get("status"), "error": record.get("error")})
        else:
            ok += 1
    return {"fetched_ok": ok, "failures": failures}


def _attractions(cached: dict) -> list[dict]:
    content = cached.get("content") or ""
    refs = [{"source": "wikivoyage", "revision_id": cached.get("revision_id")}]
    rows = [
        {"name": name, "category": "listing", "coordinate_status": "unknown", "source_refs": refs}
        for name in listing_names(content)
    ]
    seen = {row["name"] for row in rows}
    for name in mentioned_place_names(content):
        if name in seen:
            continue
        seen.add(name)
        rows.append(
            {"name": name, "category": "mentioned_in_text", "coordinate_status": "unknown", "source_refs": refs}
        )
    return rows


def build(snapshot: str, limit: int | None, activate: bool) -> dict:
    from sqlalchemy import create_engine

    from app.db.migrate import upgrade_schema_sync

    url = get_settings().database_url.replace("sqlite+aiosqlite", "sqlite")
    engine = create_engine(url)
    with engine.begin() as bind:
        upgrade_schema_sync(bind)
    engine.dispose()
    destinations = []
    failures = []
    for dest in load_registry(limit):
        title = dest.get("wikivoyage_title") or dest["name"]
        cached = fetch_extract(title, refresh=False)
        if cached.get("status") != "ok" or not (cached.get("content") or "").strip():
            failures.append({"slug": dest["slug"], "status": cached.get("status") or cached.get("error") or "missing"})
            continue
        destinations.append(
            {
                **dest,
                "country": "India",
                "source_status": "wikivoyage_extract",
                "summary": lead_excerpt(cached.get("content") or ""),
                "documents": [
                    {
                        "source_type": "wikivoyage",
                        "title": cached["title"],
                        "page_id": cached.get("page_id"),
                        "revision_id": cached.get("revision_id"),
                        "canonical_url": cached.get("canonical_url"),
                        "permalink": cached.get("permalink"),
                        "content": cached.get("content"),
                        "license_name": cached.get("license_name"),
                        "credit": cached.get("credit"),
                        "fetched_at": cached.get("fetched_revision_timestamp"),
                    }
                ],
                "attractions": _attractions(cached),
            }
        )
    if not destinations:
        raise SystemExit("No cached Wikivoyage pages were usable. Fetch failed or the cache is empty. Nothing was activated.")
    settings = get_settings()
    embedder = None
    if settings.allow_model_download or (settings.knowledge_root / "models").exists():
        embedder = get_embedder()
    result = import_corpus(
        {"snapshot_id": snapshot, "corpus_version": snapshot, "destinations": destinations, "config": {"adapter": "wikivoyage-extract-v1"}},
        embedder=embedder,
        activate=activate,
    )
    result["failures"] = failures
    result["embedding_note"] = (
        "Dense vectors were built with a local model."
        if embedder
        else "No local embedding model was opened. The snapshot supports keyword search only until a model is cached."
    )
    return result


def evaluate(strategies: list[str]) -> dict:
    """Score the reviewed case file against the active snapshot. Skips are not hits."""
    from app.rag.store import connect, corpus_stats
    from app.services.discovery_service import discover

    path = ROOT / "data" / "knowledge" / "manifests" / "eval_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    stats = corpus_stats()
    conn = connect()
    try:
        user = conn.execute("SELECT id FROM users ORDER BY created_at LIMIT 1").fetchone()
        slugs = {row["slug"] for row in conn.execute("SELECT slug FROM destinations").fetchall()}
    finally:
        conn.close()
    if user is None:
        raise SystemExit("No user row is available to attribute the retrieval trace.")
    report = []
    for strategy in strategies:
        measured = []
        skipped = []
        for case in cases:
            expected = case.get("expected_slug")
            if expected not in slugs:
                skipped.append({"id": case.get("id"), "reason": "expected_destination_not_in_snapshot"})
                continue
            found = discover(query=case["query"], user_id=user["id"], strategy=strategy)
            ranked = [row.get("slug") for row in found.get("results") or []]
            measured.append({"id": case.get("id"), "hit_at_3": expected in ranked[:3], "ranked": ranked[:3]})
        hits = sum(1 for row in measured if row["hit_at_3"])
        report.append(
            {
                "strategy": strategy,
                "measured": len(measured),
                "skipped": len(skipped),
                "hit_at_3": (hits / len(measured)) if measured else None,
                "cases": measured,
                "skipped_cases": skipped,
            }
        )
    return {"snapshot_id": stats.get("snapshot_id"), "embedding_kind": stats.get("embedding_kind"), "strategies": report}


def main() -> None:
    parser = argparse.ArgumentParser(description="Terra knowledge ingestion")
    sub = parser.add_subparsers(dest="cmd", required=True)
    fetch_p = sub.add_parser("fetch")
    fetch_p.add_argument("--limit", type=int, default=12)
    fetch_p.add_argument("--refresh", action="store_true")
    build_p = sub.add_parser("build")
    build_p.add_argument("--snapshot", default="india-v1")
    build_p.add_argument("--limit", type=int, default=12)
    build_p.add_argument("--no-activate", action="store_true")
    eval_p = sub.add_parser("evaluate")
    eval_p.add_argument("--strategy", action="append", default=None)
    args = parser.parse_args()
    if args.cmd == "fetch":
        print(json.dumps(fetch(args.limit, args.refresh), indent=2))
    elif args.cmd == "evaluate":
        print(json.dumps(evaluate(args.strategy or ["keyword"]), indent=2))
    else:
        print(json.dumps(build(args.snapshot, args.limit, activate=not args.no_activate), indent=2))


if __name__ == "__main__":
    main()
