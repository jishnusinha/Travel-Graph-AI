"""SQLite FTS5 + NumPy dense index for one active knowledge snapshot."""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from app.config import get_settings
from app.rag.embeddings import get_embedder, rerank_model_id, rerank_scores
from app.rag.fusion import cosine_scores, l2_normalize, rrf_fuse
from app.rag.graphwalk import bfs_evidence
from app.rag.intent import parse_intent, redact_query
from app.ingestion.names import name_key
from app.rag.textutil import chunk_sections, fts_match_query, sha256_text, stable_id

_NOW = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def sqlite_path() -> str:
    url = get_settings().database_url
    if "///" not in url:
        raise RuntimeError(f"Unsupported database URL for the knowledge index: {url}")
    return url.split("///", 1)[1]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(sqlite_path(), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def index_dir(snapshot_id: str) -> Path:
    path = get_settings().knowledge_root / "indexes" / snapshot_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def active_snapshot(conn: sqlite3.Connection) -> sqlite3.Row | None:
    try:
        return conn.execute(
            "SELECT * FROM knowledge_snapshots WHERE state = 'active' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    except sqlite3.OperationalError:
        return None


def import_corpus(payload: dict[str, Any], *, embedder: Any | None = None, activate: bool = True) -> dict[str, Any]:
    """Replace one snapshot's documents and, if requested, mark it active."""
    snapshot_id = str(payload["snapshot_id"])
    now = _NOW()
    conn = connect()
    try:
        _clear_snapshot(conn, snapshot_id)
        emb_kind = getattr(embedder, "kind", "unavailable") if embedder else "unavailable"
        emb_model = getattr(embedder, "model_id", "") if embedder else ""
        emb_rev = getattr(embedder, "revision", "") if embedder else ""
        emb_dim = int(getattr(embedder, "dimension", 0) or 0) if embedder else 0
        conn.execute(
            """
            INSERT INTO knowledge_snapshots (
                id, manifest_checksum, state, embedding_model, embedding_revision, embedding_dim,
                embedding_kind, corpus_version, chunk_count, document_count, config, created_at, updated_at
            ) VALUES (?, ?, 'staged', ?, ?, ?, ?, ?, 0, 0, ?, ?, ?)
            """,
            (
                snapshot_id,
                sha256_text(json.dumps(payload, sort_keys=True, default=str)[:200000]),
                emb_model,
                emb_rev,
                emb_dim,
                emb_kind,
                str(payload.get("corpus_version") or snapshot_id),
                _json(payload.get("config") or {"tokenizer": "whitespace_words_v1", "target_words": 320, "overlap_words": 50}),
                now,
                now,
            ),
        )
        chunk_rows: list[tuple[str, str]] = []
        dest_ids: list[str] = []
        for dest in payload.get("destinations") or []:
            dest_id = _upsert_destination(conn, dest, now)
            dest_ids.append(dest_id)
            for doc in dest.get("documents") or []:
                doc_id = _insert_document(conn, snapshot_id, dest_id, doc, now)
                for chunk in chunk_sections(doc.get("content") or ""):
                    cid = stable_id(
                        snapshot_id,
                        doc_id,
                        chunk["section_path"],
                        str(chunk["start_offset"]),
                        str(chunk["end_offset"]),
                        sha256_text(chunk["text"]),
                    )
                    conn.execute(
                        """
                        INSERT INTO knowledge_chunks (
                            id, snapshot_id, document_id, section_path, text, start_offset, end_offset,
                            token_count, content_hash, topic, meta, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            cid,
                            snapshot_id,
                            doc_id,
                            chunk["section_path"],
                            chunk["text"],
                            chunk["start_offset"],
                            chunk["end_offset"],
                            chunk["token_count"],
                            sha256_text(chunk["text"]),
                            doc.get("topic") or "",
                            _json({"source_type": doc.get("source_type")}),
                            now,
                            now,
                        ),
                    )
                    conn.execute(
                        "INSERT INTO chunk_destinations (id, chunk_id, destination_id, snapshot_id) VALUES (?, ?, ?, ?)",
                        (stable_id(cid, dest_id), cid, dest_id, snapshot_id),
                    )
                    conn.execute(
                        """
                        INSERT INTO knowledge_chunks_fts (chunk_id, snapshot_id, title, section, text)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (cid, snapshot_id, doc.get("title") or dest.get("name") or "", chunk["section_path"], chunk["text"]),
                    )
                    chunk_rows.append((cid, chunk["text"]))
            for attraction in dest.get("attractions") or []:
                _upsert_attraction(conn, dest_id, attraction, now)
            _collapse_attraction_names(conn, dest_id, now)
            for estimate in dest.get("estimates") or []:
                _insert_estimate(conn, snapshot_id, dest_id, estimate, now)
            for image in dest.get("images") or []:
                _insert_image(conn, snapshot_id, dest_id, image, now)
        _write_graph(conn, snapshot_id, now)
        if embedder and chunk_rows:
            vectors = l2_normalize(embedder.encode([text for _, text in chunk_rows], is_query=False))
            ids = np.array([cid for cid, _ in chunk_rows])
            np.savez_compressed(index_dir(snapshot_id) / "vectors.npz", ids=ids, vectors=vectors)
            emb_dim = int(vectors.shape[1])
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM knowledge_documents WHERE snapshot_id = ?", (snapshot_id,)
        ).fetchone()[0]
        chunk_count = len(chunk_rows)
        conn.execute(
            "UPDATE knowledge_snapshots SET chunk_count = ?, document_count = ?, embedding_dim = ?, updated_at = ? WHERE id = ?",
            (chunk_count, doc_count, emb_dim, now, snapshot_id),
        )
        if activate:
            conn.execute(
                "UPDATE knowledge_snapshots SET state = 'archived', updated_at = ? WHERE state = 'active' AND id != ?",
                (now, snapshot_id),
            )
            conn.execute(
                "UPDATE knowledge_snapshots SET state = 'active', updated_at = ? WHERE id = ?",
                (now, snapshot_id),
            )
        conn.commit()
        return {"snapshot_id": snapshot_id, "documents": doc_count, "chunks": chunk_count, "embedding_kind": emb_kind}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _clear_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> None:
    conn.execute("DELETE FROM knowledge_chunks_fts WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM chunk_destinations WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM knowledge_chunks WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM knowledge_documents WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM knowledge_relationships WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM knowledge_entities WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM travel_cost_estimates WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM destination_images WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM knowledge_snapshots WHERE id = ?", (snapshot_id,))


def _upsert_destination(conn: sqlite3.Connection, dest: dict[str, Any], now: str) -> str:
    slug = str(dest["slug"])
    dest_id = stable_id("destination", slug)
    aliases = list(dest.get("aliases") or [])
    if dest.get("name") and dest["name"] not in aliases:
        aliases.append(dest["name"])
    existing = conn.execute("SELECT id FROM destinations WHERE slug = ?", (slug,)).fetchone()
    fields = (
        dest.get("name") or slug,
        dest.get("kind") or "city",
        _json(aliases),
        dest.get("region") or "",
        dest.get("country") or "India",
        dest.get("lat"),
        dest.get("lon"),
        dest.get("coordinate_status") or ("approximate" if dest.get("lat") is not None else "unknown"),
        dest.get("wikidata_qid"),
        dest.get("wikivoyage_title"),
        dest.get("wikipedia_title"),
        dest.get("summary") or "",
        _json(dest.get("themes") or []),
        dest.get("source_status") or "pending",
        now,
    )
    if existing:
        conn.execute(
            """
            UPDATE destinations SET name=?, kind=?, aliases=?, region=?, country=?, lat=?, lon=?,
                coordinate_status=?, wikidata_qid=?, wikivoyage_title=?, wikipedia_title=?, summary=?,
                themes=?, source_status=?, updated_at=?
            WHERE id=?
            """,
            (*fields, existing["id"]),
        )
        return existing["id"]
    conn.execute(
        """
        INSERT INTO destinations (
            id, slug, name, kind, aliases, region, country, lat, lon, coordinate_status,
            wikidata_qid, wikivoyage_title, wikipedia_title, summary, themes, source_status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (dest_id, slug, *fields, now),
    )
    return dest_id


def _insert_document(conn: sqlite3.Connection, snapshot_id: str, dest_id: str, doc: dict[str, Any], now: str) -> str:
    content = doc.get("content") or ""
    revision = str(doc.get("revision_id") or sha256_text(content)[:12])
    title = doc.get("title") or ""
    doc_id = stable_id(snapshot_id, doc.get("source_type") or "document", revision, title)
    conn.execute(
        """
        INSERT INTO knowledge_documents (
            id, snapshot_id, destination_id, source_type, page_id, revision_id, title,
            canonical_url, permalink, content, content_hash, license_name, credit, fetched_at,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            doc_id,
            snapshot_id,
            dest_id,
            doc.get("source_type") or "unknown",
            str(doc.get("page_id") or ""),
            revision,
            title,
            doc.get("canonical_url") or "",
            doc.get("permalink") or "",
            content,
            sha256_text(content),
            doc.get("license_name") or "",
            doc.get("credit") or "",
            doc.get("fetched_at"),
            now,
            now,
        ),
    )
    return doc_id


def _upsert_attraction(conn: sqlite3.Connection, dest_id: str, item: dict[str, Any], now: str) -> None:
    name = item["name"]
    key = name_key(name)
    rows = conn.execute(
        "SELECT id, name, aliases, lat FROM attractions WHERE destination_id = ?",
        (dest_id,),
    ).fetchall()
    existing = next((row for row in rows if name_key(row["name"]) == key or key in _alias_keys(row["aliases"])), None)
    if existing:
        aliases = _alias_list(existing["aliases"])
        if name != existing["name"] and name not in aliases:
            aliases.append(name)
        for alias in item.get("aliases") or []:
            if alias not in aliases and alias != existing["name"]:
                aliases.append(alias)
        lat = item.get("lat") if existing["lat"] is None else None
        if lat is not None:
            conn.execute(
                """
                UPDATE attractions
                SET aliases = ?, lat = ?, lon = ?, geometry_kind = ?, osm_type = ?, osm_id = ?,
                    coordinate_status = ?, source_refs = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    _json(aliases),
                    item.get("lat"),
                    item.get("lon"),
                    item.get("geometry_kind") or "point",
                    item.get("osm_type"),
                    str(item["osm_id"]) if item.get("osm_id") is not None else None,
                    item.get("coordinate_status") or "source_provided",
                    _json(item.get("source_refs") or []),
                    now,
                    existing["id"],
                ),
            )
        else:
            conn.execute(
                "UPDATE attractions SET aliases = ?, updated_at = ? WHERE id = ?",
                (_json(aliases), now, existing["id"]),
            )
        return
    conn.execute(
        """
        INSERT INTO attractions (
            id, destination_id, name, category, aliases, lat, lon, geometry_kind, osm_type, osm_id,
            coordinate_status, source_refs, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stable_id("attraction", dest_id, name),
            dest_id,
            name,
            item.get("category") or "poi",
            _json(item.get("aliases") or []),
            item.get("lat"),
            item.get("lon"),
            item.get("geometry_kind") or "point",
            item.get("osm_type"),
            str(item["osm_id"]) if item.get("osm_id") is not None else None,
            item.get("coordinate_status") or ("source_provided" if item.get("lat") is not None else "unknown"),
            _json(item.get("source_refs") or []),
            now,
            now,
        ),
    )


def _collapse_attraction_names(conn: sqlite3.Connection, dest_id: str, now: str) -> None:
    """Keep one row when the same place was stored under a repeated name. Trip activities follow the kept id."""
    rows = conn.execute(
        "SELECT id, name, aliases, lat FROM attractions WHERE destination_id = ?",
        (dest_id,),
    ).fetchall()
    groups: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        groups.setdefault(name_key(row["name"]), []).append(row)
    for group in groups.values():
        if len(group) < 2:
            continue
        ranked = sorted(group, key=lambda row: (row["lat"] is None, row["id"]))
        keeper = ranked[0]
        aliases = _alias_list(keeper["aliases"])
        extra_ids = [row["id"] for row in ranked[1:]]
        for other in ranked[1:]:
            if other["name"] != keeper["name"] and other["name"] not in aliases:
                aliases.append(other["name"])
            for alias in _alias_list(other["aliases"]):
                if alias != keeper["name"] and alias not in aliases:
                    aliases.append(alias)
        conn.execute(
            "UPDATE attractions SET aliases = ?, updated_at = ? WHERE id = ?",
            (_json(aliases), now, keeper["id"]),
        )
        marks = ",".join("?" for _ in extra_ids)
        conn.execute(
            f"UPDATE trip_activities SET attraction_id = ? WHERE attraction_id IN ({marks})",
            (keeper["id"], *extra_ids),
        )
        conn.execute(f"DELETE FROM attractions WHERE id IN ({marks})", extra_ids)


def _alias_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item) for item in raw]
    try:
        parsed = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _alias_keys(raw: Any) -> set[str]:
    return {name_key(item) for item in _alias_list(raw) if name_key(item)}


def _insert_estimate(conn: sqlite3.Connection, snapshot_id: str, dest_id: str, item: dict[str, Any], now: str) -> None:
    conn.execute(
        """
        INSERT INTO travel_cost_estimates (
            id, destination_id, snapshot_id, category, low_inr, high_inr, currency, basis, origin,
            season, method, confidence, checked_at, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'INR', ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stable_id("estimate", snapshot_id, dest_id, item.get("category") or "", item.get("method") or ""),
            dest_id,
            snapshot_id,
            item.get("category") or "misc",
            item.get("low_inr"),
            item.get("high_inr"),
            item.get("basis") or "unknown",
            item.get("origin") or "",
            item.get("season") or "",
            item.get("method") or "",
            item.get("confidence") or "low",
            item.get("checked_at") or "",
            now,
            now,
        ),
    )


def _insert_image(conn: sqlite3.Connection, snapshot_id: str, dest_id: str, item: dict[str, Any], now: str) -> None:
    image_id = stable_id("image", snapshot_id, dest_id, item.get("source_url") or item.get("local_path") or "")
    conn.execute(
        """
        INSERT INTO destination_images (
            id, destination_id, snapshot_id, local_path, author, license_name, license_url, source_url,
            width, height, alt, attribution, content_hash, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            image_id,
            dest_id,
            snapshot_id,
            item.get("local_path") or "",
            item.get("author") or "",
            item.get("license_name") or "",
            item.get("license_url") or "",
            item.get("source_url") or "",
            item.get("width"),
            item.get("height"),
            item.get("alt") or "",
            item.get("attribution") or "",
            item.get("content_hash") or "",
            now,
            now,
        ),
    )
    if item.get("hero"):
        conn.execute("UPDATE destinations SET cover_image_id = ? WHERE id = ?", (image_id, dest_id))


def _write_graph(conn: sqlite3.Connection, snapshot_id: str, now: str) -> None:
    destinations = conn.execute(
        """
        SELECT DISTINCT d.* FROM destinations d
        JOIN chunk_destinations cd ON cd.destination_id = d.id
        WHERE cd.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    entities: dict[str, str] = {}
    for dest in destinations:
        eid = stable_id("entity", snapshot_id, "destination", dest["id"])
        entities[dest["id"]] = eid
        conn.execute(
            """
            INSERT INTO knowledge_entities (
                id, snapshot_id, entity_type, label, external_key, aliases, ref_id, created_at, updated_at
            ) VALUES (?, ?, 'destination', ?, ?, ?, ?, ?, ?)
            """,
            (eid, snapshot_id, dest["name"], f"destination:{dest['slug']}", dest["aliases"], dest["id"], now, now),
        )
        region = (dest["region"] or "").strip()
        if region:
            rid = stable_id("entity", snapshot_id, "region", region)
            if region not in entities:
                entities[region] = rid
                conn.execute(
                    """
                    INSERT OR IGNORE INTO knowledge_entities (
                        id, snapshot_id, entity_type, label, external_key, aliases, ref_id, created_at, updated_at
                    ) VALUES (?, ?, 'region', ?, ?, '[]', NULL, ?, ?)
                    """,
                    (rid, snapshot_id, region, f"region:{region}", now, now),
                )
            conn.execute(
                """
                INSERT INTO knowledge_relationships (
                    id, snapshot_id, subject_id, predicate, object_id, evidence_chunk_id, method, confidence, created_at, updated_at
                ) VALUES (?, ?, ?, 'located_in', ?, NULL, 'registry', 1.0, ?, ?)
                """,
                (stable_id("edge", eid, "located_in", rid), snapshot_id, eid, rid, now, now),
            )
    attractions = conn.execute(
        """
        SELECT a.* FROM attractions a
        WHERE a.destination_id IN (
            SELECT destination_id FROM chunk_destinations WHERE snapshot_id = ?
        )
        """,
        (snapshot_id,),
    ).fetchall()
    for attraction in attractions:
        aid = stable_id("entity", snapshot_id, "attraction", attraction["id"])
        conn.execute(
            """
            INSERT INTO knowledge_entities (
                id, snapshot_id, entity_type, label, external_key, aliases, ref_id, created_at, updated_at
            ) VALUES (?, ?, 'attraction', ?, ?, ?, ?, ?, ?)
            """,
            (
                aid,
                snapshot_id,
                attraction["name"],
                f"attraction:{attraction['id']}",
                attraction["aliases"],
                attraction["id"],
                now,
                now,
            ),
        )
        parent = entities.get(attraction["destination_id"])
        if parent:
            chunk = conn.execute(
                """
                SELECT c.id FROM knowledge_chunks c
                JOIN chunk_destinations cd ON cd.chunk_id = c.id
                WHERE cd.destination_id = ? AND cd.snapshot_id = ? AND lower(c.text) LIKE ?
                LIMIT 1
                """,
                (attraction["destination_id"], snapshot_id, f"%{attraction['name'].lower()}%"),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO knowledge_relationships (
                    id, snapshot_id, subject_id, predicate, object_id, evidence_chunk_id, method, confidence, created_at, updated_at
                ) VALUES (?, ?, ?, 'located_in', ?, ?, ?, 1.0, ?, ?)
                """,
                (
                    stable_id("edge", aid, "located_in", parent),
                    snapshot_id,
                    aid,
                    parent,
                    chunk["id"] if chunk else None,
                    "mention_in_chunk" if chunk else "structured_record",
                    now,
                    now,
                ),
            )
    coords = [d for d in destinations if d["lat"] is not None and d["lon"] is not None]
    for i, left in enumerate(coords):
        for right in coords[i + 1 :]:
            km = haversine_km(left["lat"], left["lon"], right["lat"], right["lon"])
            if km <= 80:
                conn.execute(
                    """
                    INSERT INTO knowledge_relationships (
                        id, snapshot_id, subject_id, predicate, object_id, evidence_chunk_id, method, confidence, created_at, updated_at
                    ) VALUES (?, ?, ?, 'within_80km_straight_line', ?, NULL, 'haversine', ?, ?, ?)
                    """,
                    (
                        stable_id("edge", entities[left["id"]], "near", entities[right["id"]]),
                        snapshot_id,
                        entities[left["id"]],
                        entities[right["id"]],
                        round(km, 3),
                        now,
                        now,
                    ),
                )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlmb = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlmb / 2) ** 2
    return float(2 * r * np.arcsin(np.sqrt(a)))


def alias_map(conn: sqlite3.Connection) -> dict[str, str]:
    rows = conn.execute("SELECT slug, name, aliases FROM destinations").fetchall()
    out: dict[str, str] = {}
    for row in rows:
        out[row["name"].lower()] = row["slug"]
        out[row["slug"].lower()] = row["slug"]
        try:
            aliases = json.loads(row["aliases"] or "[]")
        except json.JSONDecodeError:
            aliases = []
        for alias in aliases:
            out[str(alias).lower()] = row["slug"]
    return out


def search_sync(
    *,
    query: str,
    user_id: str,
    strategy: str | None = None,
    filters: dict[str, Any] | None = None,
    top_k: int | None = None,
    mode: str = "evidence",
    node_id: str = "",
    agent_run_id: str | None = None,
    embedder: Any | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    settings = get_settings()
    filters = dict(filters or {})
    requested = strategy or settings.retrieval_strategy
    top_k = min(int(top_k or settings.retrieval_top_k), 50)
    final_k = min(int(settings.rerank_top_k), 10)
    warnings: list[str] = []
    timings: dict[str, float] = {}
    conn = connect()
    try:
        t0 = time.perf_counter()
        snap = active_snapshot(conn)
        if filters.get("snapshot_id"):
            snap = conn.execute(
                "SELECT * FROM knowledge_snapshots WHERE id = ?", (filters["snapshot_id"],)
            ).fetchone()
        if snap is None:
            return _empty("snapshot_missing", "No active knowledge snapshot. Build one with scripts/ingest.ps1.")
        snapshot_id = snap["id"]
        intent = parse_intent(query, filters, alias_map(conn))
        if intent.get("destination_slug") and not filters.get("destination_slug"):
            filters["destination_slug"] = intent["destination_slug"]
        timings["normalize_ms"] = _ms(t0)
        chunks = _load_chunks(conn, snapshot_id)
        allowed = set(chunks)
        if filters.get("destination_slug"):
            allowed = {cid for cid, row in chunks.items() if row["slug"] == filters["destination_slug"]}
        if filters.get("region"):
            region = str(filters["region"]).lower()
            allowed = {cid for cid in allowed if (chunks[cid]["region"] or "").lower() == region}

        keyword_ids: list[str] = []
        dense_ids: list[str] = []
        t1 = time.perf_counter()
        match = fts_match_query(query)
        if match:
            try:
                rows = conn.execute(
                    """
                    SELECT chunk_id, bm25(knowledge_chunks_fts) AS score
                    FROM knowledge_chunks_fts
                    WHERE knowledge_chunks_fts MATCH ? AND snapshot_id = ?
                    ORDER BY score ASC, chunk_id ASC
                    LIMIT ?
                    """,
                    (match, snapshot_id, top_k * 3),
                ).fetchall()
                keyword_ids = [row["chunk_id"] for row in rows if row["chunk_id"] in allowed][:top_k]
                keyword_scores = {row["chunk_id"]: float(row["score"]) for row in rows}
            except sqlite3.OperationalError:
                warnings.append("fts_query_rejected")
                keyword_scores = {}
        else:
            warnings.append("empty_fts_query")
            keyword_scores = {}
        timings["fts_ms"] = _ms(t1)

        t2 = time.perf_counter()
        dense_scores: dict[str, float] = {}
        if requested in {"dense", "hybrid", "hybrid_rerank", "graph_hybrid"}:
            embedder = embedder or get_embedder()
            matrix, ids = _load_vectors(snapshot_id)
            block = _dense_block_reason(snap, embedder, matrix)
            if block:
                warnings.append(block)
            else:
                qv = l2_normalize(embedder.encode([query], is_query=True))[0]
                scores = cosine_scores(matrix, qv)
                order = sorted(range(len(ids)), key=lambda i: (-float(scores[i]), ids[i]))
                for i in order:
                    cid = ids[i]
                    if cid in allowed:
                        dense_ids.append(cid)
                        dense_scores[cid] = float(scores[i])
                    if len(dense_ids) >= top_k:
                        break
        timings["dense_ms"] = _ms(t2)

        graph_ids: list[str] = []
        t3 = time.perf_counter()
        if requested == "graph_hybrid":
            graph_ids = _graph_candidates(conn, snapshot_id, chunks, keyword_ids or dense_ids, intent)
            if not graph_ids:
                warnings.append("graph_empty")
        timings["graph_ms"] = _ms(t3)

        lists: list[list[str]] = []
        if requested == "keyword":
            lists = [keyword_ids]
            applied = "keyword" if keyword_ids else "unavailable"
        elif requested == "dense":
            lists = [dense_ids]
            applied = "dense" if dense_ids else "unavailable"
        else:
            if keyword_ids:
                lists.append(keyword_ids)
            if dense_ids:
                lists.append(dense_ids)
            if graph_ids:
                lists.append(graph_ids)
            if keyword_ids and dense_ids:
                applied = "hybrid"
            elif keyword_ids:
                applied = "keyword"
                if requested != "keyword":
                    warnings.append("fell_back_to_keyword")
            elif dense_ids:
                applied = "dense"
                if requested != "dense":
                    warnings.append("fell_back_to_dense")
            else:
                applied = "unavailable"
        if requested == "graph_hybrid" and graph_ids and applied == "hybrid":
            applied = "graph_hybrid"
        present = [lst for lst in lists if lst]
        fused = rrf_fuse(present) if present else []
        timings["fusion_ms"] = 0.0

        pool = [cid for cid, _ in fused[: max(top_k, final_k)] if cid in chunks]
        t4 = time.perf_counter()
        reranked = False
        ranking = list(fused)
        score_kind = "rrf" if len(present) > 1 else applied
        if requested == "hybrid_rerank" and pool:
            texts = [chunks[cid]["text"] for cid in pool]
            scores = rerank_scores(query, texts)
            if scores is None or len(scores) != len(pool):
                warnings.append("rerank_unavailable")
            else:
                reranked = True
                order = sorted(range(len(pool)), key=lambda i: (-float(scores[i]), pool[i]))
                ranking = [(pool[i], float(scores[i])) for i in order]
                score_kind = "cross_encoder"
                if keyword_ids and dense_ids:
                    applied = "hybrid_rerank"
                else:
                    warnings.append("rerank_on_partial_candidates")
                    applied = f"{applied}+rerank" if applied != "unavailable" else applied
        timings["rerank_ms"] = _ms(t4)

        chosen: list[str] = []
        per_dest: dict[str, int] = {}
        cap = 4 if mode == "discovery" else final_k
        for cid, _score in ranking:
            row = chunks.get(cid)
            if row is None:
                continue
            key = row["destination_id"] or cid
            if mode == "discovery" and per_dest.get(key, 0) >= cap:
                continue
            chosen.append(cid)
            per_dest[key] = per_dest.get(key, 0) + 1
            if len(chosen) >= final_k:
                break
        chosen_set = set(chosen)

        now = _NOW()
        run_id = stable_id("retrieval", user_id, snapshot_id, query, requested, now, str(time.time_ns()))
        # stable_id is uuid5 so time_ns makes it unique; that's fine for run ids.
        conn.execute(
            """
            INSERT INTO retrieval_runs (
                id, user_id, agent_run_id, node_id, query_redacted, intent, snapshot_id,
                strategy_requested, strategy_applied, config_hash, timings_ms, status, warnings,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                agent_run_id,
                node_id,
                redact_query(query),
                _json(intent),
                snapshot_id,
                requested,
                applied,
                sha256_text(f"{requested}|{top_k}|{snap['embedding_model']}|{snap['embedding_kind']}"),
                _json({k: round(v, 3) for k, v in timings.items()}),
                _json(warnings),
                now,
                now,
            ),
        )
        stage_rows = [
            ("keyword", keyword_ids, keyword_scores, "bm25"),
            ("dense", dense_ids, dense_scores, "cosine"),
            ("rrf", [cid for cid, _ in fused], {cid: score for cid, score in fused}, "rrf"),
            ("rerank", [cid for cid, _ in ranking] if reranked else [], {cid: score for cid, score in ranking} if reranked else {}, "cross_encoder"),
        ]
        for stage, ids, scores, kind in stage_rows:
            for rank, cid in enumerate(ids, start=1):
                conn.execute(
                    """
                    INSERT INTO retrieval_hits (
                        id, retrieval_run_id, chunk_id, stage, rank, raw_score, score_kind, chosen, rejection_reason, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        stable_id(run_id, stage, cid),
                        run_id,
                        cid,
                        stage,
                        rank,
                        scores.get(cid),
                        kind,
                        1 if cid in chosen_set else 0,
                        "" if cid in chosen_set else "not_in_final",
                        now,
                        now,
                    ),
                )
        citations = []
        for rank, cid in enumerate(chosen, start=1):
            row = chunks[cid]
            citation_id = stable_id("citation", run_id, cid)
            excerpt = row["text"][:700]
            conn.execute(
                """
                INSERT INTO citations (
                    id, snapshot_id, chunk_id, document_id, title, section_path, excerpt, permalink,
                    license_name, source_type, owner_user_id, retrieval_run_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    citation_id,
                    snapshot_id,
                    cid,
                    row["document_id"],
                    row["title"],
                    row["section_path"],
                    excerpt,
                    row["permalink"],
                    row["license_name"],
                    row["source_type"],
                    user_id,
                    run_id,
                    now,
                    now,
                ),
            )
            citations.append(
                {
                    "citation_id": citation_id,
                    "chunk_id": cid,
                    "destination_id": row["destination_id"],
                    "slug": row["slug"],
                    "name": row["name"],
                    "region": row["region"],
                    "title": row["title"],
                    "section_path": row["section_path"],
                    "text": row["text"],
                    "excerpt": excerpt,
                    "permalink": row["permalink"],
                    "license_name": row["license_name"],
                    "source_type": row["source_type"],
                    "rank": rank,
                    "score_kind": score_kind,
                }
            )
        conn.commit()
        timings["total_ms"] = _ms(started)
        return {
            "status": "completed",
            "snapshot_id": snapshot_id,
            "embedding_kind": snap["embedding_kind"],
            "embedding_model": snap["embedding_model"],
            "retrieval_run_id": run_id,
            "intent": intent,
            "strategy_requested": requested,
            "strategy_applied": applied,
            "warnings": warnings,
            "timings_ms": {k: round(v, 3) for k, v in timings.items()},
            "reranked": reranked,
            "rerank_model": rerank_model_id() if reranked else "",
            "evidence": citations,
            "keyword_count": len(keyword_ids),
            "dense_count": len(dense_ids),
            "graph_count": len(graph_ids),
        }
    finally:
        conn.close()


def _empty(status: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "snapshot_id": None,
        "retrieval_run_id": None,
        "intent": {},
        "strategy_requested": "",
        "strategy_applied": "unavailable",
        "warnings": [message],
        "timings_ms": {},
        "evidence": [],
        "embedding_kind": "unavailable",
        "embedding_model": "",
        "reranked": False,
    }


def _load_chunks(conn: sqlite3.Connection, snapshot_id: str) -> dict[str, dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT c.id AS chunk_id, c.text, c.section_path, c.document_id,
               doc.title, doc.license_name, doc.permalink, doc.source_type,
               cd.destination_id, d.slug, d.name, d.region
        FROM knowledge_chunks c
        JOIN knowledge_documents doc ON doc.id = c.document_id
        LEFT JOIN chunk_destinations cd ON cd.chunk_id = c.id
        LEFT JOIN destinations d ON d.id = cd.destination_id
        WHERE c.snapshot_id = ?
        """,
        (snapshot_id,),
    ).fetchall()
    return {row["chunk_id"]: dict(row) for row in rows}


def _dense_block_reason(snap: sqlite3.Row, embedder: Any, matrix: np.ndarray | None) -> str | None:
    """Why dense search cannot run. None means the snapshot vectors match this model."""
    if embedder is None or matrix is None or matrix.size == 0:
        return "dense_unavailable"
    snap_model = snap["embedding_model"] or ""
    if snap_model and snap_model != getattr(embedder, "model_id", ""):
        return "dense_model_mismatch"
    snap_kind = snap["embedding_kind"] or ""
    kind = getattr(embedder, "kind", "")
    if snap_kind and snap_kind != kind:
        return "dense_model_mismatch"
    snap_dim = int(snap["embedding_dim"] or 0)
    dimension = int(getattr(embedder, "dimension", 0) or 0)
    if snap_dim and dimension and snap_dim != dimension:
        return "dense_dimension_mismatch"
    if matrix.ndim != 2 or matrix.shape[1] != dimension:
        return "dense_dimension_mismatch"
    return None


def _load_vectors(snapshot_id: str) -> tuple[np.ndarray | None, list[str]]:
    path = index_dir(snapshot_id) / "vectors.npz"
    if not path.exists():
        return None, []
    with np.load(path, allow_pickle=False) as data:
        ids = [str(x) for x in data["ids"].tolist()]
        vectors = np.asarray(data["vectors"], dtype=np.float32)
    return vectors, ids


def _graph_candidates(conn, snapshot_id: str, chunks: dict, seed_chunks: list[str], intent: dict) -> list[str]:
    hops = max(1, min(int(get_settings().graph_max_hops), 2))
    edges = [
        dict(row)
        for row in conn.execute(
            """
            SELECT subject_id, predicate, object_id, evidence_chunk_id, method
            FROM knowledge_relationships WHERE snapshot_id = ?
            """,
            (snapshot_id,),
        ).fetchall()
    ]
    seeds = []
    if intent.get("destination_slug"):
        row = conn.execute(
            "SELECT id FROM knowledge_entities WHERE snapshot_id = ? AND external_key = ?",
            (snapshot_id, f"destination:{intent['destination_slug']}"),
        ).fetchone()
        if row:
            seeds.append(row["id"])
    for cid in seed_chunks[:5]:
        dest_id = chunks.get(cid, {}).get("destination_id")
        if not dest_id:
            continue
        row = conn.execute(
            "SELECT id FROM knowledge_entities WHERE snapshot_id = ? AND ref_id = ? AND entity_type = 'destination'",
            (snapshot_id, dest_id),
        ).fetchone()
        if row:
            seeds.append(row["id"])
    walked = bfs_evidence(seed_entity_ids=list(dict.fromkeys(seeds)), edges=edges, max_hops=hops)
    chunk_ids = []
    for edge in walked:
        cid = edge.get("evidence_chunk_id")
        if cid and cid not in chunk_ids:
            chunk_ids.append(cid)
    return chunk_ids


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


def corpus_stats() -> dict[str, Any]:
    conn = connect()
    try:
        snap = active_snapshot(conn)
        if snap is None:
            return {
                "status": "snapshot_missing",
                "snapshot_id": None,
                "destinations": 0,
                "documents": 0,
                "chunks": 0,
                "attractions": 0,
                "images": 0,
                "embedding_kind": "unavailable",
                "embedding_model": "",
                "fts": _fts_ready(conn),
                "capabilities": _capabilities(None),
            }
        def count(sql: str, arg: tuple) -> int:
            return int(conn.execute(sql, arg).fetchone()[0])

        return {
            "status": "ready",
            "snapshot_id": snap["id"],
            "state": snap["state"],
            "destinations": count(
                "SELECT COUNT(DISTINCT destination_id) FROM chunk_destinations WHERE snapshot_id = ?",
                (snap["id"],),
            ),
            "documents": int(snap["document_count"] or 0),
            "chunks": int(snap["chunk_count"] or 0),
            "attractions": count(
                """
                SELECT COUNT(*) FROM attractions WHERE destination_id IN (
                    SELECT destination_id FROM chunk_destinations WHERE snapshot_id = ?
                )
                """,
                (snap["id"],),
            ),
            "images": count("SELECT COUNT(*) FROM destination_images WHERE snapshot_id = ?", (snap["id"],)),
            "entities": count("SELECT COUNT(*) FROM knowledge_entities WHERE snapshot_id = ?", (snap["id"],)),
            "relationships": count("SELECT COUNT(*) FROM knowledge_relationships WHERE snapshot_id = ?", (snap["id"],)),
            "license_coverage": {
                row["license_name"] or "unknown": row["n"]
                for row in conn.execute(
                    """
                    SELECT license_name, COUNT(*) AS n
                    FROM knowledge_documents
                    WHERE snapshot_id = ?
                    GROUP BY license_name
                    ORDER BY n DESC
                    """,
                    (snap["id"],),
                ).fetchall()
            },
            "image_licenses": {
                row["license_name"] or "unknown": row["n"]
                for row in conn.execute(
                    """
                    SELECT license_name, COUNT(*) AS n
                    FROM destination_images
                    WHERE snapshot_id = ?
                    GROUP BY license_name
                    ORDER BY n DESC
                    """,
                    (snap["id"],),
                ).fetchall()
            },
            "embedding_kind": snap["embedding_kind"],
            "embedding_model": snap["embedding_model"],
            "embedding_dim": snap["embedding_dim"],
            "corpus_version": snap["corpus_version"],
            "fts": _fts_ready(conn),
            "capabilities": _capabilities(snap),
            "source_status_note": "Counts are rows in the active snapshot, not a target inventory.",
        }
    finally:
        conn.close()


def _fts_ready(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'knowledge_chunks_fts'"
    ).fetchone()
    return row is not None


def _capabilities(snap: sqlite3.Row | None) -> dict[str, Any]:
    settings = get_settings()
    dense = bool(snap and snap["embedding_kind"] in {"fastembed", "sentence_transformer"} and (index_dir(snap["id"]) / "vectors.npz").exists())
    return {
        "keyword": bool(snap),
        "dense": dense,
        "hybrid": dense,
        "rerank": False,
        "graph": bool(snap),
        "visual_similarity": False,
        "live_llm": settings.ai_mode == "openai" and settings.openai_ready,
        "network_tools": settings.allow_network_tools,
        "map_mode": settings.map_mode,
        "knowledge_mode": settings.knowledge_mode,
    }
