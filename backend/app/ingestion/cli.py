"""Build a snapshot from the cached Wikivoyage extracts and the destination registry.

Usage (from backend/, with the venv active):
  python -m app.ingestion.cli fetch --limit 12
  python -m app.ingestion.cli build --snapshot india-v1
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from app.config import ROOT, get_settings
from app.ingestion.commons import fetch_image
from app.ingestion.http import cache_file, read_cache
from app.ingestion.names import dedupe_named
from app.ingestion.osm import fetch_named_pois
from app.ingestion.wikipedia import fetch_page
from app.ingestion.wikivoyage import fetch_extract, lead_excerpt, listing_names, mentioned_place_names
from app.rag.embeddings import get_embedder
from app.rag.store import import_corpus


def registry_path() -> Path:
    return ROOT / "data" / "knowledge" / "manifests" / "destinations.json"


def load_registry(limit: int | None) -> list[dict]:
    payload = json.loads(registry_path().read_text(encoding="utf-8"))
    rows = payload["destinations"]
    return rows[:limit] if limit else rows


def fetch(limit: int | None, refresh: bool, sources: set[str] | None = None) -> dict:
    selected = sources or {"wikivoyage", "wikipedia", "osm", "commons"}
    failures = []
    ok = 0
    wikipedia_ok = 0
    osm_ok = 0
    images_ok = 0
    for dest in load_registry(limit):
        title = dest.get("wikivoyage_title") or dest["name"]
        record = {"status": "skipped"}
        if "wikivoyage" in selected:
            record = fetch_extract(title, refresh=refresh)
            if record.get("status") != "ok" or not (record.get("content") or "").strip():
                failures.append({"slug": dest["slug"], "source": "wikivoyage", "title": title, "status": record.get("status"), "error": record.get("error")})
            else:
                ok += 1
        wiki_title = dest.get("wikipedia_title") or dest["name"]
        wiki = read_cache(cache_file("wikipedia", wiki_title)) or {"status": "missing", "content": ""}
        if "wikipedia" in selected:
            if refresh or not cache_file("wikipedia", wiki_title).exists():
                time.sleep(0.35)
            wiki = fetch_page(wiki_title, refresh=refresh)
            if wiki.get("status") == "ok" and (wiki.get("content") or "").strip():
                wikipedia_ok += 1
            else:
                failures.append({"slug": dest["slug"], "source": "wikipedia", "title": wiki_title, "status": wiki.get("status"), "error": wiki.get("error")})
        elif wiki.get("status") == "ok":
            wikipedia_ok += 1
        if "osm" in selected:
            center = _center(dest, wiki)
            if center is not None:
                if refresh or not cache_file("osm", dest["slug"]).exists():
                    time.sleep(1.5)
                pois = fetch_named_pois(dest["slug"], center[0], center[1], refresh=refresh)
                if pois.get("status") == "ok":
                    osm_ok += 1
                else:
                    failures.append({"slug": dest["slug"], "source": "openstreetmap", "status": pois.get("status"), "error": pois.get("error")})
        if "commons" in selected:
            if refresh or not cache_file("commons", dest["slug"]).exists():
                time.sleep(0.35)
            image = fetch_image(dest["slug"], wiki.get("title") or wiki_title, refresh=refresh)
            if image.get("status") == "ok":
                images_ok += 1
            else:
                failures.append({"slug": dest["slug"], "source": "commons", "status": image.get("status"), "error": image.get("error")})
    return {
        "fetched_ok": ok,
        "wikipedia_ok": wikipedia_ok,
        "osm_ok": osm_ok,
        "images_ok": images_ok,
        "failures": failures,
    }


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


def _center(dest: dict, wiki: dict) -> tuple[float, float] | None:
    if dest.get("lat") is not None and dest.get("lon") is not None:
        return float(dest["lat"]), float(dest["lon"])
    if wiki.get("lat") is not None and wiki.get("lon") is not None:
        return float(wiki["lat"]), float(wiki["lon"])
    return None


def _cost_estimates(kind: str) -> list[dict]:
    path = ROOT / "data" / "knowledge" / "manifests" / "cost_ranges.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    band = (payload.get("by_kind") or {}).get(kind) or (payload.get("by_kind") or {}).get("city") or {}
    return [
        {
            "category": category,
            "low_inr": span.get("low_inr"),
            "high_inr": span.get("high_inr"),
            "basis": span.get("basis"),
            "method": payload.get("method"),
            "confidence": payload.get("confidence") or "low",
            "checked_at": payload.get("checked_at") or "",
        }
        for category, span in band.items()
        if isinstance(span, dict)
    ]


def _source_document(record: dict) -> dict | None:
    if record.get("status") != "ok" or not (record.get("content") or "").strip():
        return None
    return {
        "source_type": record.get("source_type") or "unknown",
        "title": record.get("title"),
        "page_id": record.get("page_id"),
        "revision_id": record.get("revision_id"),
        "canonical_url": record.get("canonical_url"),
        "permalink": record.get("permalink"),
        "content": record.get("content"),
        "license_name": record.get("license_name"),
        "credit": record.get("credit"),
        "fetched_at": record.get("fetched_revision_timestamp"),
    }


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
    image_count = 0
    for dest in load_registry(limit):
        title = dest.get("wikivoyage_title") or dest["name"]
        cached = fetch_extract(title, refresh=False)
        wiki_title = dest.get("wikipedia_title") or dest["name"]
        wiki = read_cache(cache_file("wikipedia", wiki_title)) or {"status": "missing", "content": ""}
        documents = [doc for doc in (_source_document(cached), _source_document(wiki)) if doc]
        if not documents:
            failures.append({"slug": dest["slug"], "status": cached.get("status") or wiki.get("status") or "missing"})
            continue
        merged = dict(dest)
        if merged.get("lat") is None and wiki.get("lat") is not None:
            merged["lat"] = wiki["lat"]
            merged["lon"] = wiki["lon"]
            merged["coordinate_status"] = wiki.get("coordinate_status") or "wikipedia_page"
        if wiki.get("wikidata_qid"):
            merged["wikidata_qid"] = wiki["wikidata_qid"]
        if wiki.get("title"):
            merged["wikipedia_title"] = wiki["title"]
        pois = read_cache(cache_file("osm", merged["slug"])) or {}
        osm_rows = list(pois.get("attractions") or [])
        image = read_cache(cache_file("commons", merged["slug"])) or {}
        images = []
        if image.get("status") == "ok" and image.get("local_path"):
            images.append({**image, "hero": True})
            image_count += 1
        summary_source = cached if cached.get("status") == "ok" and (cached.get("content") or "").strip() else wiki
        destinations.append(
            {
                **merged,
                "country": "India",
                "source_status": "wikivoyage_extract" if summary_source is cached else "wikipedia_extract",
                "summary": lead_excerpt(summary_source.get("content") or ""),
                "documents": documents,
                "attractions": dedupe_named(_attractions(cached) + osm_rows),
                "estimates": _cost_estimates(str(merged.get("kind") or "city")),
                "images": images,
            }
        )
    if not destinations:
        raise SystemExit("No cached Wikivoyage pages were usable. Fetch failed or the cache is empty. Nothing was activated.")
    embedder = get_embedder()
    result = import_corpus(
        {"snapshot_id": snapshot, "corpus_version": snapshot, "destinations": destinations, "config": {"adapter": "wikivoyage-extract-v1"}},
        embedder=embedder,
        activate=activate,
    )
    result["failures"] = failures
    result["images"] = image_count
    result["embedding_note"] = (
        "Dense vectors were built with a local model."
        if embedder
        else "No local embedding model was opened. The snapshot supports keyword search only until a model is cached."
    )
    manifest_dir = get_settings().knowledge_root / "snapshots" / snapshot
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "snapshot_id": snapshot,
        "documents": result.get("documents"),
        "chunks": result.get("chunks"),
        "images": image_count,
        "embedding_kind": result.get("embedding_kind"),
        "destinations": len(destinations),
        "failures": failures,
        "cost_method": "editorial_planning_band",
        "adapters": ["wikivoyage-extract-v1", "wikipedia-intro-v1", "osm-named-poi-v1", "commons-hero-v1"],
    }
    (manifest_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    result["manifest"] = str(manifest_dir / "manifest.json")
    return result


def prepare_models() -> dict:
    """Download and open the pinned embedding and cross-encoder models."""
    from app.rag.embeddings import (
        clear_model_cache,
        load_embedder,
        load_reranker,
        rerank_kind,
        rerank_model_id,
        rerank_scores,
    )

    settings = get_settings()
    clear_model_cache()
    embedder = load_embedder(local_only=False)
    if embedder is None:
        raise SystemExit(
            "Could not download or open the embedding model. "
            "Check network access and EMBEDDING_MODEL, then run this command again."
        )
    vector = embedder.encode(["waterfalls in the hills"], is_query=True)
    if vector.ndim != 2 or vector.shape[1] != embedder.dimension:
        raise SystemExit("The embedding model opened but returned an unexpected vector shape.")
    clear_model_cache()
    reranker = load_reranker(local_only=False)
    scores = rerank_scores("waterfalls", ["Nohkalikai Falls is a waterfall.", "A beach market sells spices."])
    if reranker is None or scores is None or len(scores) != 2:
        raise SystemExit(
            "Could not download or open the cross-encoder. "
            "Check network access and RERANK_MODEL, then run this command again."
        )
    manifest = {
        "embedding_model": embedder.model_id,
        "embedding_kind": embedder.kind,
        "embedding_revision": embedder.revision,
        "embedding_dim": embedder.dimension,
        "rerank_model": rerank_model_id(),
        "rerank_kind": rerank_kind(),
        "configured_rerank_model": settings.rerank_model,
    }
    path = settings.knowledge_root / "models" / "terra-model-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest"] = str(path)
    return manifest


def verify_retrieval() -> dict:
    """Run keyword, dense, hybrid and reranked search on the active travel snapshot."""
    from app.rag.store import connect, corpus_stats, search_sync

    stats = corpus_stats()
    if stats.get("status") != "ready":
        raise SystemExit(stats.get("message") or "No active knowledge snapshot.")
    conn = connect()
    try:
        user = conn.execute("SELECT id FROM users ORDER BY created_at LIMIT 1").fetchone()
    finally:
        conn.close()
    if user is None:
        raise SystemExit("No user row is available to attribute the retrieval trace.")
    queries = ["Nohkalikai Falls", "quiet hills and waterfalls", "beaches"]
    strategies = ["keyword", "dense", "hybrid", "hybrid_rerank"]
    runs = []
    failures = []
    for strategy in strategies:
        for query in queries:
            found = search_sync(query=query, user_id=user["id"], strategy=strategy, mode="evidence")
            titles = []
            for item in (found.get("evidence") or [])[:3]:
                titles.append(item.get("name") or item.get("title"))
            row = {
                "query": query,
                "requested": strategy,
                "applied": found.get("strategy_applied"),
                "warnings": found.get("warnings") or [],
                "keyword_count": found.get("keyword_count"),
                "dense_count": found.get("dense_count"),
                "reranked": found.get("reranked"),
                "rerank_model": found.get("rerank_model"),
                "timings_ms": found.get("timings_ms"),
                "top": titles,
                "embedding_kind": found.get("embedding_kind"),
            }
            runs.append(row)
            if query == "Nohkalikai Falls" and found.get("strategy_applied") != strategy:
                failures.append({"query": query, "requested": strategy, "applied": found.get("strategy_applied"), "warnings": found.get("warnings")})
            blob = " ".join((item.get("text") or "") for item in (found.get("evidence") or []))
            if query == "Nohkalikai Falls" and "Nohkalikai" not in blob:
                failures.append({"query": query, "strategy": strategy, "reason": "named waterfall missing from evidence"})
    report = {
        "snapshot_id": stats.get("snapshot_id"),
        "documents": stats.get("documents"),
        "chunks": stats.get("chunks"),
        "embedding_kind": stats.get("embedding_kind"),
        "embedding_model": stats.get("embedding_model"),
        "runs": runs,
        "failures": failures,
    }
    if failures:
        print(json.dumps(report, indent=2))
        raise SystemExit(1)
    return report


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
    fetch_p.add_argument("--limit", type=int, default=0, help="0 uses the full destination registry")
    fetch_p.add_argument("--refresh", action="store_true")
    fetch_p.add_argument("--source", action="append", default=None, choices=["wikivoyage", "wikipedia", "osm", "commons"])
    build_p = sub.add_parser("build")
    build_p.add_argument("--snapshot", default="india-v1")
    build_p.add_argument("--limit", type=int, default=0, help="0 uses the full destination registry")
    build_p.add_argument("--no-activate", action="store_true")
    eval_p = sub.add_parser("evaluate")
    eval_p.add_argument("--strategy", action="append", default=None)
    sub.add_parser("prepare-models")
    sub.add_parser("verify-retrieval")
    args = parser.parse_args()
    if args.cmd == "fetch":
        print(json.dumps(fetch(args.limit, args.refresh, set(args.source) if args.source else None), indent=2))
    elif args.cmd == "evaluate":
        print(json.dumps(evaluate(args.strategy or ["keyword"]), indent=2))
    elif args.cmd == "prepare-models":
        print(json.dumps(prepare_models(), indent=2))
    elif args.cmd == "verify-retrieval":
        print(json.dumps(verify_retrieval(), indent=2))
    else:
        print(json.dumps(build(args.snapshot, args.limit, activate=not args.no_activate), indent=2))


if __name__ == "__main__":
    main()
