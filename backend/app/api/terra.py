"""Terra discovery, corpus and retrieval routes."""

from __future__ import annotations

import re
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_csrf
from app.config import get_settings
from app.db.session import get_db
from app.models import SavedDestination, User, UserPreferences
from app.rag.store import connect, corpus_stats
from app.schemas.common import APIModel
from app.rag.runtime import offload
from app.services.discovery_service import answer_about, compare_destinations, discover, _photo
from app.rag.store import search_sync

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

router = APIRouter(tags=["terra"], dependencies=[Depends(require_csrf)])
public_router = APIRouter(tags=["terra-public"])


class SearchIn(APIModel):
    query: str = Field(min_length=2, max_length=1000)
    filters: dict[str, Any] = Field(default_factory=dict)
    strategy: Optional[str] = None


class CompareIn(APIModel):
    destination_ids: list[str] = Field(min_length=2, max_length=3)
    preferences: list[str] = Field(default_factory=list)


class AskIn(APIModel):
    query: str = Field(min_length=2, max_length=1000)


class SaveIn(APIModel):
    destination_id: str


class PersonalizationIn(APIModel):
    consent: bool
    interests: list[str] = Field(default_factory=list)


class RetrievalBenchIn(APIModel):
    strategies: list[str] = Field(default_factory=lambda: ["keyword", "hybrid_rerank"])
    limit: int = Field(default=10, ge=1, le=30)


def _snapshot_required(result: dict) -> dict:
    if result.get("status") == "snapshot_missing":
        raise HTTPException(status_code=503, detail=result.get("warnings", ["Knowledge snapshot is not active"])[0])
    return result


@public_router.get("/knowledge/stats")
async def knowledge_stats() -> dict:
    return corpus_stats()


@public_router.get("/knowledge/highlights")
async def highlights(limit: int = Query(default=8, ge=1, le=24)) -> dict:
    stats = corpus_stats()
    if stats.get("status") != "ready":
        return {"snapshot_id": None, "items": [], "status": stats.get("status")}
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT d.id, d.slug, d.name, d.region, d.summary, d.themes, d.source_status, d.coordinate_status,
                   MAX(CASE WHEN di.local_path IS NOT NULL AND di.local_path != '' THEN 1 ELSE 0 END) AS has_photo
            FROM destinations d
            JOIN chunk_destinations cd ON cd.destination_id = d.id
            LEFT JOIN destination_images di ON di.destination_id = d.id
            WHERE cd.snapshot_id = ?
            GROUP BY d.id
            ORDER BY has_photo DESC, d.name
            LIMIT ?
            """,
            (stats["snapshot_id"], limit),
        ).fetchall()
        items = [_dest_summary(row, conn) for row in rows]
    finally:
        conn.close()
    return {"snapshot_id": stats["snapshot_id"], "items": items, "status": "ready"}


@public_router.get("/knowledge/media/{slug}")
async def knowledge_media(slug: str):
    """Serve one stored Commons file for a destination. Path stays under the knowledge assets root."""
    if not _SLUG_RE.match(slug):
        raise HTTPException(status_code=404, detail="Image not found")
    stats = corpus_stats()
    if stats.get("status") != "ready":
        raise HTTPException(status_code=404, detail="Image not found")
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT di.local_path, di.alt
            FROM destination_images di
            JOIN destinations d ON d.id = di.destination_id
            JOIN chunk_destinations cd ON cd.destination_id = d.id
            WHERE d.slug = ? AND cd.snapshot_id = ? AND di.local_path != ''
            LIMIT 1
            """,
            (slug, stats["snapshot_id"]),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Image not found")
    root = get_settings().knowledge_root.resolve()
    assets = (root / "assets").resolve()
    target = (root / row["local_path"]).resolve()
    try:
        target.relative_to(assets)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Image not found") from exc
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Image not found")
    media = "image/jpeg" if target.suffix.lower() in {".jpg", ".jpeg"} else "application/octet-stream"
    if target.suffix.lower() == ".png":
        media = "image/png"
    elif target.suffix.lower() == ".webp":
        media = "image/webp"
    return FileResponse(target, media_type=media, filename=target.name, content_disposition_type="inline")


@router.get("/destinations")
async def list_destinations(
    q: Optional[str] = Query(default=None, max_length=120),
    region: Optional[str] = None,
    limit: int = Query(default=24, ge=1, le=100),
    user: User = Depends(get_current_user),
) -> dict:
    del user
    stats = corpus_stats()
    if stats.get("status") != "ready":
        raise HTTPException(status_code=503, detail="Knowledge snapshot is not active")
    conn = connect()
    try:
        sql = """
            SELECT d.* FROM destinations d
            JOIN chunk_destinations cd ON cd.destination_id = d.id
            WHERE cd.snapshot_id = ?
        """
        args: list[Any] = [stats["snapshot_id"]]
        if region:
            sql += " AND lower(d.region) = lower(?)"
            args.append(region)
        if q:
            sql += " AND (lower(d.name) LIKE ? OR lower(d.region) LIKE ?)"
            like = f"%{q.lower()}%"
            args.extend([like, like])
        sql += " GROUP BY d.id ORDER BY d.name LIMIT ?"
        args.append(limit)
        rows = conn.execute(sql, args).fetchall()
        items = [_dest_summary(row, conn) for row in rows]
    finally:
        conn.close()
    return {
        "snapshot_id": stats["snapshot_id"],
        "items": items,
    }


@router.post("/destinations/compare")
async def compare(payload: CompareIn, user: User = Depends(get_current_user)) -> dict:
    del user
    return compare_destinations(payload.destination_ids, payload.preferences)


@router.get("/destinations/{slug}")
async def destination_detail(slug: str, user: User = Depends(get_current_user)) -> dict:
    del user
    conn = connect()
    try:
        row = conn.execute("SELECT * FROM destinations WHERE slug = ?", (slug,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Destination not found")
        attractions = conn.execute(
            "SELECT id, name, category, lat, lon, coordinate_status FROM attractions WHERE destination_id = ? ORDER BY name",
            (row["id"],),
        ).fetchall()
        estimates = conn.execute(
            "SELECT category, low_inr, high_inr, basis, method, confidence, season, origin FROM travel_cost_estimates WHERE destination_id = ?",
            (row["id"],),
        ).fetchall()
        images = conn.execute(
            "SELECT id, alt, author, license_name, license_url, source_url, attribution, local_path FROM destination_images WHERE destination_id = ?",
            (row["id"],),
        ).fetchall()
        docs = conn.execute(
            """
            SELECT id, title, source_type, license_name, credit, permalink, canonical_url, revision_id
            FROM knowledge_documents WHERE destination_id = ?
            """,
            (row["id"],),
        ).fetchall()
        destination = _dest_summary(row, conn)
        image_rows = []
        for image in images:
            payload = dict(image)
            if payload.get("local_path"):
                payload["url"] = f"/api/v1/knowledge/media/{row['slug']}"
            image_rows.append(payload)
        payload = {
            "destination": destination,
            "summary": row["summary"],
            "source_status": row["source_status"],
            "coordinate_status": row["coordinate_status"],
            "attractions": [dict(a) for a in attractions],
            "estimates": [dict(e) for e in estimates],
            "images": image_rows,
            "sources": [dict(d) for d in docs],
            "network_tools": {
                "weather": None,
                "routing": None,
                "reason": "ALLOW_NETWORK_TOOLS is false. Straight-line distances are not driving routes."
                if not get_settings().allow_network_tools
                else "Optional adapters are enabled.",
            },
        }
    finally:
        conn.close()
    return payload


@router.get("/destinations/{slug}/attractions")
async def destination_attractions(slug: str, category: Optional[str] = None, user: User = Depends(get_current_user)) -> dict:
    detail = await destination_detail(slug, user)
    items = detail["attractions"]
    if category:
        items = [a for a in items if a["category"] == category]
    return {"items": items}


@router.post("/destinations/{slug}/ask")
async def ask(slug: str, payload: AskIn, user: User = Depends(get_current_user)) -> dict:
    return _snapshot_required(await offload(answer_about, slug, payload.query, user.id))


@router.get("/knowledge/entities")
async def knowledge_entities(
    q: Optional[str] = Query(default=None, max_length=120),
    entity_type: Optional[str] = Query(default=None, max_length=40),
    limit: int = Query(default=40, ge=1, le=100),
    user: User = Depends(get_current_user),
) -> dict:
    del user
    stats = corpus_stats()
    if stats.get("status") != "ready":
        raise HTTPException(status_code=503, detail="Knowledge snapshot is not active")
    conn = connect()
    try:
        sql = """
            SELECT id, entity_type, label, external_key, ref_id
            FROM knowledge_entities
            WHERE snapshot_id = ?
        """
        args: list[Any] = [stats["snapshot_id"]]
        if entity_type:
            sql += " AND entity_type = ?"
            args.append(entity_type)
        if q:
            sql += " AND lower(label) LIKE ?"
            args.append(f"%{q.lower()}%")
        sql += " ORDER BY entity_type, label LIMIT ?"
        args.append(limit)
        rows = conn.execute(sql, args).fetchall()
    finally:
        conn.close()
    return {"snapshot_id": stats["snapshot_id"], "items": [dict(row) for row in rows]}


@router.get("/destinations/{slug}/graph")
async def destination_graph(
    slug: str,
    hops: int = Query(default=1, ge=1, le=2),
    predicate: Optional[str] = Query(default=None, max_length=64),
    user: User = Depends(get_current_user),
) -> dict:
    del user
    from app.rag.graphwalk import bfs_evidence

    conn = connect()
    try:
        dest = conn.execute("SELECT id, slug, name FROM destinations WHERE slug = ?", (slug,)).fetchone()
        if dest is None:
            raise HTTPException(status_code=404, detail="Destination not found")
        stats = corpus_stats()
        if stats.get("status") != "ready":
            raise HTTPException(status_code=503, detail="Knowledge snapshot is not active")
        entity = conn.execute(
            "SELECT id FROM knowledge_entities WHERE snapshot_id = ? AND ref_id = ? AND entity_type = 'destination'",
            (stats["snapshot_id"], dest["id"]),
        ).fetchone()
        if entity is None:
            entity = conn.execute(
                "SELECT id FROM knowledge_entities WHERE snapshot_id = ? AND external_key = ?",
                (stats["snapshot_id"], f"destination:{slug}"),
            ).fetchone()
        if entity is None:
            return {
                "nodes": [],
                "edges": [],
                "seed": None,
                "snapshot_id": stats["snapshot_id"],
                "note": "No destination entity is stored for this slug.",
            }
        edge_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT id, subject_id, predicate, object_id, evidence_chunk_id, method, confidence
                FROM knowledge_relationships
                WHERE snapshot_id = ?
                """,
                (stats["snapshot_id"],),
            ).fetchall()
        ]
        if predicate:
            edge_rows = [edge for edge in edge_rows if edge["predicate"] == predicate]
        walked = bfs_evidence(seed_entity_ids=[entity["id"]], edges=edge_rows, max_hops=hops)
        if hops == 1:
            # Keep direct edges even when they have no further expansion.
            direct = [edge for edge in edge_rows if edge["subject_id"] == entity["id"] or edge["object_id"] == entity["id"]]
            seen_ids = {edge["id"] for edge in walked}
            for edge in direct:
                if edge["id"] not in seen_ids:
                    walked.append({**edge, "hop": 1, "via": entity["id"]})
        ids = {entity["id"]}
        for edge in walked:
            ids.add(edge["subject_id"])
            ids.add(edge["object_id"])
        nodes = []
        if ids:
            qmarks = ",".join("?" for _ in ids)
            nodes = [
                dict(row)
                for row in conn.execute(
                    f"SELECT id, entity_type, label, external_key, ref_id FROM knowledge_entities WHERE id IN ({qmarks})",
                    tuple(ids),
                ).fetchall()
            ]
        evidence = {}
        chunk_ids = [edge["evidence_chunk_id"] for edge in walked if edge.get("evidence_chunk_id")]
        if chunk_ids:
            qmarks = ",".join("?" for _ in chunk_ids)
            for row in conn.execute(
                f"""
                SELECT id, section_path, substr(text, 1, 280) AS excerpt
                FROM knowledge_chunks WHERE id IN ({qmarks})
                """,
                tuple(chunk_ids),
            ).fetchall():
                evidence[row["id"]] = {
                    "chunk_id": row["id"],
                    "section_path": row["section_path"],
                    "excerpt": row["excerpt"],
                }
        edges = []
        for edge in walked:
            item = dict(edge)
            if edge.get("evidence_chunk_id") and edge["evidence_chunk_id"] in evidence:
                item["evidence"] = evidence[edge["evidence_chunk_id"]]
            edges.append(item)
    finally:
        conn.close()
    return {
        "snapshot_id": stats["snapshot_id"],
        "seed": {"id": entity["id"], "slug": dest["slug"], "name": dest["name"]},
        "hops": hops,
        "predicate": predicate,
        "nodes": nodes,
        "edges": edges,
        "note": "within_80km_straight_line is haversine, not a road connection. Graph edges are not transport routes.",
    }


@router.post("/discovery/search")
async def discovery_search(payload: SearchIn, user: User = Depends(get_current_user)) -> dict:
    return _snapshot_required(
        await offload(
            discover,
            query=payload.query,
            user_id=user.id,
            filters=payload.filters,
            strategy=payload.strategy,
        )
    )


@router.post("/retrieval/search")
async def retrieval_search(payload: SearchIn, user: User = Depends(get_current_user)) -> dict:
    result = await offload(
        search_sync,
        query=payload.query,
        user_id=user.id,
        strategy=payload.strategy,
        filters=payload.filters,
    )
    return _snapshot_required(result)


@router.get("/retrieval/runs/{run_id}")
async def retrieval_run(run_id: str, user: User = Depends(get_current_user)) -> dict:
    conn = connect()
    try:
        run = conn.execute("SELECT * FROM retrieval_runs WHERE id = ? AND user_id = ?", (run_id, user.id)).fetchone()
        if run is None:
            raise HTTPException(status_code=404, detail="Retrieval run not found")
        hits = conn.execute(
            "SELECT chunk_id, stage, rank, raw_score, score_kind, chosen, rejection_reason FROM retrieval_hits WHERE retrieval_run_id = ? ORDER BY stage, rank",
            (run_id,),
        ).fetchall()
    finally:
        conn.close()
    body = dict(run)
    body["hits"] = [dict(h) for h in hits]
    return body


@router.get("/knowledge/sources/{source_id}")
async def source(source_id: str, user: User = Depends(get_current_user)) -> dict:
    conn = connect()
    try:
        citation = conn.execute("SELECT * FROM citations WHERE id = ?", (source_id,)).fetchone()
        if citation is not None:
            owner = citation["owner_user_id"]
            if owner and owner != user.id:
                raise HTTPException(status_code=404, detail="Source not found")
            return {
                "id": citation["id"],
                "snapshot_id": citation["snapshot_id"],
                "title": citation["title"],
                "section_path": citation["section_path"],
                "excerpt": citation["excerpt"],
                "permalink": citation["permalink"],
                "license": citation["license_name"],
                "source_type": citation["source_type"],
            }
        chunk = conn.execute(
            """
            SELECT c.id, c.text, c.section_path, c.snapshot_id, d.title, d.license_name, d.permalink, d.source_type
            FROM knowledge_chunks c JOIN knowledge_documents d ON d.id = c.document_id
            WHERE c.id = ?
            """,
            (source_id,),
        ).fetchone()
    finally:
        conn.close()
    if chunk is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return {
        "id": chunk["id"],
        "snapshot_id": chunk["snapshot_id"],
        "title": chunk["title"],
        "section_path": chunk["section_path"],
        "excerpt": chunk["text"][:700],
        "permalink": chunk["permalink"],
        "license": chunk["license_name"],
        "source_type": chunk["source_type"],
    }


@router.get("/saved-destinations")
async def list_saved(user: User = Depends(get_current_user)) -> dict:
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.destination_id, s.created_at, d.slug, d.name, d.region, d.source_status
            FROM saved_destinations s JOIN destinations d ON d.id = s.destination_id
            WHERE s.user_id = ? ORDER BY s.created_at DESC
            """,
            (user.id,),
        ).fetchall()
    finally:
        conn.close()
    return {"items": [dict(r) for r in rows]}


@router.post("/saved-destinations")
async def save_destination(payload: SaveIn, user: User = Depends(get_current_user)) -> dict:
    conn = connect()
    try:
        dest = conn.execute(
            "SELECT id FROM destinations WHERE id = ? OR slug = ?",
            (payload.destination_id, payload.destination_id),
        ).fetchone()
        if dest is None:
            raise HTTPException(status_code=404, detail="Destination not found")
        existing = conn.execute(
            "SELECT id FROM saved_destinations WHERE user_id = ? AND destination_id = ?",
            (user.id, dest["id"]),
        ).fetchone()
        if existing:
            return {"id": existing["id"], "destination_id": dest["id"], "created": False}
        from app.rag.textutil import stable_id
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        sid = stable_id("saved", user.id, dest["id"])
        conn.execute(
            "INSERT INTO saved_destinations (id, user_id, destination_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (sid, user.id, dest["id"], now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return {"id": sid, "destination_id": dest["id"], "created": True}


@router.delete("/saved-destinations/{saved_id}")
async def unsave(saved_id: str, user: User = Depends(get_current_user)) -> dict:
    conn = connect()
    try:
        cur = conn.execute(
            "DELETE FROM saved_destinations WHERE id = ? AND user_id = ?",
            (saved_id, user.id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Saved place not found")
    finally:
        conn.close()
    return {"deleted": True}


@router.post("/me/personalization")
async def set_personalization(
    payload: PersonalizationIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    prefs = (
        await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))
    ).scalar_one_or_none()
    if prefs is None:
        raise HTTPException(status_code=404, detail="Preferences not found")
    extra = dict(prefs.extra or {})
    extra["terra_personalization_consent"] = bool(payload.consent)
    if payload.consent and payload.interests:
        prefs.interests = list(payload.interests)
    elif not payload.consent:
        extra.pop("terra_interest_profile", None)
    prefs.extra = extra
    await db.commit()
    return {"consent": bool(payload.consent)}


@router.get("/discovery/for-you")
async def for_you(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> dict:
    prefs = (
        await db.execute(select(UserPreferences).where(UserPreferences.user_id == user.id))
    ).scalar_one_or_none()
    extra = (prefs.extra if prefs else {}) or {}
    if not extra.get("terra_personalization_consent"):
        raise HTTPException(
            status_code=403,
            detail="Personalization is off until you explicitly consent. Saved places are not used to rank results.",
        )
    interests = " ".join(str(i) for i in (prefs.interests if prefs else []))
    if not interests.strip():
        return {"results": [], "generation_mode": "explicit_interest_match", "note": "No stated interests yet."}
    found = await offload(discover, query=interests, user_id=user.id, strategy="keyword")
    found["generation_mode"] = "explicit_interest_match"
    found["note"] = "Ranked from interests you saved, using keyword retrieval. This is not inferred tracking."
    return found


@router.post("/discovery/visual")
async def visual_search(user: User = Depends(get_current_user)) -> dict:
    del user
    raise HTTPException(
        status_code=503,
        detail="No local image-similarity model is installed. Visual search is unavailable and was not approximated.",
    )


@router.post("/evaluations/retrieval")
async def retrieval_benchmark(payload: RetrievalBenchIn, user: User = Depends(get_current_user)) -> dict:
    """Run the reviewed case file. Cases whose expected place is absent are skipped, not scored as hits."""
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parents[3] / "data" / "knowledge" / "manifests" / "eval_cases.json"
    if not path.exists():
        raise HTTPException(status_code=503, detail="No reviewed retrieval cases file is present.")
    cases = json.loads(path.read_text(encoding="utf-8"))
    stats = corpus_stats()
    if stats.get("status") != "ready":
        raise HTTPException(status_code=503, detail="Knowledge snapshot is not active")
    conn = connect()
    try:
        slugs = {row["slug"] for row in conn.execute("SELECT slug FROM destinations").fetchall()}
    finally:
        conn.close()
    strategies = payload.strategies[:6]
    report = []
    for strategy in strategies:
        measured = []
        skipped = []
        for case in cases[: payload.limit]:
            expected = case.get("expected_slug")
            if expected not in slugs:
                skipped.append({"id": case.get("id"), "reason": "expected_destination_not_in_snapshot"})
                continue
            found = await offload(discover, query=case["query"], user_id=user.id, strategy=strategy)
            slugs_ranked = [r.get("slug") for r in found.get("results") or []]
            hit = expected in slugs_ranked[:3]
            measured.append({"id": case.get("id"), "hit_at_3": hit, "ranked": slugs_ranked[:3]})
        hits = sum(1 for row in measured if row["hit_at_3"])
        report.append(
            {
                "strategy": strategy,
                "measured": len(measured),
                "skipped": len(skipped),
                "hit_at_3": (hits / len(measured)) if measured else None,
                "cases": measured,
                "skipped_cases": skipped,
                "score_provenance": "measured" if measured else "not_applicable",
            }
        )
    return {
        "snapshot_id": stats.get("snapshot_id"),
        "embedding_kind": stats.get("embedding_kind"),
        "dataset": "eval_cases.json",
        "strategies": report,
        "judge": "not_applicable",
    }


def _dest_summary(row, conn=None) -> dict:
    import json

    try:
        themes = json.loads(row["themes"] or "[]")
    except (TypeError, json.JSONDecodeError):
        themes = row["themes"] if isinstance(row["themes"], list) else []
    photo = None
    if conn is not None:
        photo = _photo(conn, row["id"], row["slug"])
    return {
        "destination_id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "region": row["region"],
        "kind": row["kind"] if "kind" in row.keys() else None,
        "summary": row["summary"],
        "themes": themes,
        "source_status": row["source_status"],
        "coordinate_status": row["coordinate_status"],
        "lat": row["lat"] if "lat" in row.keys() else None,
        "lon": row["lon"] if "lon" in row.keys() else None,
        "photo": photo,
    }
