"""Terra discovery, corpus and retrieval routes."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, require_csrf
from app.config import get_settings
from app.db.session import get_db
from app.models import SavedDestination, User, UserPreferences
from app.rag.store import connect, corpus_stats
from app.schemas.common import APIModel
from app.services.discovery_service import answer_about, compare_destinations, discover
from app.rag.store import search_sync

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
            SELECT d.id, d.slug, d.name, d.region, d.summary, d.themes, d.source_status, d.coordinate_status
            FROM destinations d
            JOIN chunk_destinations cd ON cd.destination_id = d.id
            WHERE cd.snapshot_id = ?
            GROUP BY d.id
            ORDER BY d.name
            LIMIT ?
            """,
            (stats["snapshot_id"], limit),
        ).fetchall()
    finally:
        conn.close()
    items = []
    for row in rows:
        import json

        try:
            themes = json.loads(row["themes"] or "[]")
        except json.JSONDecodeError:
            themes = []
        items.append(
            {
                "destination_id": row["id"],
                "slug": row["slug"],
                "name": row["name"],
                "region": row["region"],
                "summary": row["summary"],
                "themes": themes,
                "source_status": row["source_status"],
                "coordinate_status": row["coordinate_status"],
                "photo": None,
            }
        )
    return {"snapshot_id": stats["snapshot_id"], "items": items, "status": "ready"}


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
    finally:
        conn.close()
    return {
        "snapshot_id": stats["snapshot_id"],
        "items": [_dest_summary(row) for row in rows],
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
    finally:
        conn.close()
    return {
        "destination": _dest_summary(row),
        "summary": row["summary"],
        "source_status": row["source_status"],
        "coordinate_status": row["coordinate_status"],
        "attractions": [dict(a) for a in attractions],
        "estimates": [dict(e) for e in estimates],
        "images": [dict(i) for i in images],
        "sources": [dict(d) for d in docs],
        "network_tools": {
            "weather": None,
            "routing": None,
            "reason": "ALLOW_NETWORK_TOOLS is false. Straight-line distances are not driving routes."
            if not get_settings().allow_network_tools
            else "Optional adapters are enabled.",
        },
    }


@router.get("/destinations/{slug}/attractions")
async def destination_attractions(slug: str, category: Optional[str] = None, user: User = Depends(get_current_user)) -> dict:
    detail = await destination_detail(slug, user)
    items = detail["attractions"]
    if category:
        items = [a for a in items if a["category"] == category]
    return {"items": items}


@router.post("/destinations/{slug}/ask")
async def ask(slug: str, payload: AskIn, user: User = Depends(get_current_user)) -> dict:
    return _snapshot_required(answer_about(slug, payload.query, user.id))


@router.get("/destinations/{slug}/graph")
async def destination_graph(slug: str, user: User = Depends(get_current_user)) -> dict:
    del user
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
            return {"nodes": [], "edges": [], "snapshot_id": stats["snapshot_id"]}
        edges = conn.execute(
            """
            SELECT id, subject_id, predicate, object_id, evidence_chunk_id, method, confidence
            FROM knowledge_relationships
            WHERE snapshot_id = ? AND (subject_id = ? OR object_id = ?)
            """,
            (stats["snapshot_id"], entity["id"], entity["id"]),
        ).fetchall()
        ids = {entity["id"]}
        for edge in edges:
            ids.add(edge["subject_id"])
            ids.add(edge["object_id"])
        nodes = []
        if ids:
            qmarks = ",".join("?" for _ in ids)
            nodes = conn.execute(
                f"SELECT id, entity_type, label, external_key FROM knowledge_entities WHERE id IN ({qmarks})",
                tuple(ids),
            ).fetchall()
    finally:
        conn.close()
    return {
        "snapshot_id": stats["snapshot_id"],
        "nodes": [dict(n) for n in nodes],
        "edges": [dict(e) for e in edges],
        "note": "within_80km_straight_line is haversine, not a road connection.",
    }


@router.post("/discovery/search")
async def discovery_search(payload: SearchIn, user: User = Depends(get_current_user)) -> dict:
    return _snapshot_required(
        discover(query=payload.query, user_id=user.id, filters=payload.filters, strategy=payload.strategy)
    )


@router.post("/retrieval/search")
async def retrieval_search(payload: SearchIn, user: User = Depends(get_current_user)) -> dict:
    result = search_sync(query=payload.query, user_id=user.id, strategy=payload.strategy, filters=payload.filters)
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
    found = discover(query=interests, user_id=user.id, strategy="keyword")
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
    strategies = payload.strategies[:4]
    report = []
    for strategy in strategies:
        measured = []
        skipped = []
        for case in cases[: payload.limit]:
            expected = case.get("expected_slug")
            if expected not in slugs:
                skipped.append({"id": case.get("id"), "reason": "expected_destination_not_in_snapshot"})
                continue
            found = discover(query=case["query"], user_id=user.id, strategy=strategy)
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


def _dest_summary(row) -> dict:
    import json

    try:
        themes = json.loads(row["themes"] or "[]")
    except (TypeError, json.JSONDecodeError):
        themes = row["themes"]
    return {
        "destination_id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "region": row["region"],
        "kind": row["kind"],
        "summary": row["summary"],
        "themes": themes,
        "source_status": row["source_status"],
        "coordinate_status": row["coordinate_status"],
        "lat": row["lat"],
        "lon": row["lon"],
    }
