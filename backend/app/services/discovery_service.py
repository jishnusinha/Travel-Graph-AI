"""Discovery grouping and grounded Q&A over retrieval evidence."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.rag.compose import compose_answer
from app.rag.store import connect, haversine_km, search_sync
from app.rag.textutil import significant_terms


def discover(
    *,
    query: str,
    user_id: str,
    filters: dict[str, Any] | None = None,
    strategy: str | None = None,
    embedder: Any | None = None,
) -> dict[str, Any]:
    found = search_sync(
        query=query,
        user_id=user_id,
        strategy=strategy,
        filters=filters,
        mode="discovery",
        node_id="discovery",
        embedder=embedder,
    )
    if found.get("status") != "completed":
        return found
    grouped: dict[str, dict[str, Any]] = {}
    for item in found.get("evidence") or []:
        slug = item.get("slug") or ""
        bucket = grouped.setdefault(
            slug,
            {
                "destination_id": item.get("destination_id"),
                "slug": slug,
                "name": item.get("name"),
                "region": item.get("region"),
                "evidence": [],
                "score": 0.0,
            },
        )
        if len(bucket["evidence"]) < 3:
            bucket["evidence"].append(item)
            bucket["score"] += 1.0 / item.get("rank", 1)
    results = []
    interests = set((found.get("intent") or {}).get("interests") or [])
    for rank, bucket in enumerate(sorted(grouped.values(), key=lambda b: (-b["score"], b["slug"] or "")), start=1):
        blob = " ".join(ev["text"] for ev in bucket["evidence"])
        matched = sorted(interests & _matched_interests(blob))
        profile = _profile(bucket["destination_id"])
        unknown = ["crowd_level", "live_prices"]
        if not profile["has_estimate"]:
            unknown.append("budget_fit")
        results.append(
            {
                "destination_id": bucket["destination_id"],
                "slug": bucket["slug"],
                "name": bucket["name"],
                "region": bucket["region"],
                "summary": profile["summary"],
                "themes": profile.get("themes") or [],
                "photo": profile.get("photo"),
                "rank": rank,
                "matched_preferences": matched,
                "unknown_preferences": unknown,
                "evidence": [_public_evidence(ev) for ev in bucket["evidence"]],
                "evidence_count": len(bucket["evidence"]),
                "source_status": profile["source_status"],
            }
        )
    return {
        **{k: found[k] for k in (
            "snapshot_id", "retrieval_run_id", "intent", "strategy_requested", "strategy_applied",
            "warnings", "timings_ms", "embedding_kind", "embedding_model", "status",
        )},
        "results": results,
        "generation_mode": "deterministic_evidence",
        "insufficient_evidence": len(results) == 0,
    }


def answer_about(slug: str, query: str, user_id: str, *, embedder: Any | None = None) -> dict[str, Any]:
    found = search_sync(
        query=query,
        user_id=user_id,
        filters={"destination_slug": slug},
        mode="evidence",
        node_id="destination_qa",
        embedder=embedder,
    )
    if found.get("status") != "completed":
        return found
    composed = compose_answer(query, found.get("evidence") or [])
    return {
        "snapshot_id": found.get("snapshot_id"),
        "retrieval_run_id": found.get("retrieval_run_id"),
        "strategy_applied": found.get("strategy_applied"),
        "embedding_kind": found.get("embedding_kind"),
        "warnings": found.get("warnings") or [],
        "generation_mode": "deterministic_evidence",
        **composed,
        "citations": [_public_evidence(ev) for ev in found.get("evidence") or []],
    }


def compare_destinations(ids: list[str], preferences: list[str] | None = None) -> dict[str, Any]:
    conn = connect()
    try:
        rows = []
        for dest_id in ids:
            row = conn.execute("SELECT * FROM destinations WHERE id = ? OR slug = ?", (dest_id, dest_id)).fetchone()
            if row is None:
                continue
            attractions = conn.execute(
                "SELECT name, category, lat, lon, coordinate_status FROM attractions WHERE destination_id = ?",
                (row["id"],),
            ).fetchall()
            estimates = conn.execute(
                "SELECT category, low_inr, high_inr, basis, method, confidence FROM travel_cost_estimates WHERE destination_id = ?",
                (row["id"],),
            ).fetchall()
            rows.append(
                {
                    "destination_id": row["id"],
                    "slug": row["slug"],
                    "name": row["name"],
                    "region": row["region"],
                    "kind": row["kind"],
                    "coordinate_status": row["coordinate_status"],
                    "source_status": row["source_status"],
                    "themes": _loads(row["themes"]),
                    "attraction_count": len(attractions),
                    "attractions": [dict(a) for a in attractions[:8]],
                    "estimates": [dict(e) for e in estimates],
                    "summary": row["summary"],
                    "missing": _missing(row, estimates),
                }
            )
        return {
            "preferences": preferences or [],
            "results": rows,
            "note": "Comparison uses stored corpus fields only. Missing estimates are unknown, not zero.",
        }
    finally:
        conn.close()


def _matched_interests(text: str) -> set[str]:
    from app.rag.intent import INTEREST_SYNONYMS

    lowered = text.lower()
    found = set()
    for key, words in INTEREST_SYNONYMS.items():
        if any(word in lowered for word in words):
            found.add(key)
    return found


def _public_evidence(ev: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": ev.get("citation_id"),
        "chunk_id": ev.get("chunk_id"),
        "title": ev.get("title"),
        "section_path": ev.get("section_path"),
        "excerpt": ev.get("excerpt"),
        "permalink": ev.get("permalink") or "",
        "license": ev.get("license_name"),
        "source_type": ev.get("source_type"),
        "rank": ev.get("rank"),
    }


def _profile(destination_id: str | None) -> dict[str, Any]:
    empty = {"source_status": "unknown", "summary": "", "has_estimate": False, "themes": [], "photo": None}
    if not destination_id:
        return empty
    conn = connect()
    try:
        row = conn.execute(
            "SELECT id, slug, source_status, summary, themes FROM destinations WHERE id = ?", (destination_id,)
        ).fetchone()
        estimate = conn.execute(
            "SELECT 1 FROM travel_cost_estimates WHERE destination_id = ? LIMIT 1", (destination_id,)
        ).fetchone()
        if row is None:
            return empty
        return {
            "source_status": row["source_status"],
            "summary": row["summary"] or "",
            "has_estimate": estimate is not None,
            "themes": _loads(row["themes"]),
            "photo": _photo(conn, row["id"], row["slug"]),
        }
    finally:
        conn.close()


def _photo(conn: sqlite3.Connection, destination_id: str, slug: str) -> dict[str, Any] | None:
    image = conn.execute(
        """
        SELECT alt, author, license_name, license_url, source_url, attribution, local_path
        FROM destination_images
        WHERE destination_id = ? AND local_path != ''
        ORDER BY created_at
        LIMIT 1
        """,
        (destination_id,),
    ).fetchone()
    if image is None:
        return None
    return {
        "url": f"/api/v1/knowledge/media/{slug}",
        "alt": image["alt"] or "",
        "author": image["author"] or "",
        "license_name": image["license_name"] or "",
        "license_url": image["license_url"] or "",
        "source_url": image["source_url"] or "",
        "attribution": image["attribution"] or "",
    }


def _loads(raw: str | None) -> list:
    try:
        value = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return value if isinstance(value, list) else []


def _missing(row: sqlite3.Row, estimates) -> list[str]:
    missing = []
    if row["lat"] is None or row["lon"] is None:
        missing.append("coordinates")
    if not estimates:
        missing.append("cost_estimates")
    if not (row["summary"] or "").strip():
        missing.append("summary")
    return missing


def straight_line_note(points: list[tuple[float, float]]) -> list[dict[str, Any]]:
    notes = []
    for i in range(len(points) - 1):
        km = haversine_km(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        notes.append({"from_index": i, "to_index": i + 1, "straight_line_km": round(km, 1), "route": "not_computed"})
    return notes


def supported_terms(query: str, text: str) -> set[str]:
    return significant_terms(query) & significant_terms(text)
