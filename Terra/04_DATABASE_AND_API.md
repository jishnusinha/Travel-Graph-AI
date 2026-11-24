# 04 — Data model, migrations and REST contracts

Use existing SQLAlchemy, SQLite, async sessions, Alembic and Pydantic patterns. Inspect actual schema first; proposed names may be adjusted with documented mapping. Do not replace users/trips/agent tables or delete existing data. Add migration `0002_terra_knowledge` or next available revision; test upgrade on a copy of legacy DB and fresh DB, preserve existing run IDs and trip versions. Enable FK constraints per connection; use short transactions and indexes; do not hold DB locks during model inference or remote calls.

## Shared knowledge tables

| Table | Key fields and constraints |
|---|---|
| destinations | id PK, slug unique, name, kind, aliases JSON, region, country, lat/lon nullable, canonical external IDs, cover_image_id nullable, created/updated |
| attractions | id PK, destination_id FK or join for multiple locations, name, category, aliases, lat/lon, geometry_kind, osm_type/id, external IDs, source refs; unique external ID when present |
| knowledge_snapshots | id PK, manifest checksum, created_at, state staged/active/archived, embedding model/revision/dim, corpus config |
| knowledge_documents | id PK, snapshot_id FK, source type, page ID, revision ID, canonical URL/permalink, title, content, hash, license/credit, fetched_at; unique snapshot+source+revision |
| knowledge_chunks | id or composite snapshot/chunk key, document FK, section, text, offsets, token_count, hash, metadata, vector row ID; unique within snapshot |
| chunk_destinations / chunk_entities | many-to-many mappings with FK and indices for destination/topic filters |
| destination_images | destination FK, local path, author, license URL, source file URL, dimensions, modification, attribution, alt, hash, snapshot ref |
| travel_cost_estimates | destination FK, category, low/high, currency, basis per_person/per_room/per_party, origin, season, source/method, checked_at, confidence |
| knowledge_entities | stable id, type, label, external ID, aliases, snapshot ref |
| knowledge_relationships | snapshot, subject_id, predicate, object_id, evidence chunk or structured source ID, confidence/method; no unsupported relationships |
| ingestion_runs | snapshot, adapter version, status, timestamps, counts and sanitized failures |

FTS5 virtual table over chunk ID, title, section, text; use migration and parameterized search. Maintain FTS rows on snapshot import and validate count. No dynamic SQL interpolating user query. Snapshot membership for destinations/attractions/images must preserve historical versions or snapshot the evidence separately. Local dense index stores ordered chunk IDs + normalized vectors + metadata checksums in versioned artifacts; never assume row order without manifest validation.

## User/run-specific data

| Table / extension | Fields |
|---|---|
| saved_destinations | user_id + destination_id unique, created_at; cascade on user removal |
| retrieval_runs | id, user_id, nullable agent_run_id, node_id, query (redact sensitive values), normalized intent/filters, snapshot ID, strategy, config hash, timing, status, created_at |
| retrieval_hits | retrieval_run_id, chunk_id, stage, rank, raw score, score kind, chosen flag, rejection reason; preserve source snapshot |
| citations | id, snapshot_id, chunk/source ref, exact excerpt, document revision/permalink, source license; link to trip version, activity and/or answer claim with ownership enforced |
| trip_activity extension | nullable attraction_id, coordinates/duration, citation refs, estimate provenance, verification status; backward compatible |
| trip_version extension | snapshot ID, plan schema version, exact supporting evidence, route/cost provenance; old versions remain readable |
| agent_run extension | knowledge_mode, snapshot, graph version, selected evidence refs, parent run if clarification, generation provenance |
| evaluation extension | dataset and rubric version, strategy, snapshot, score provenance, sample count, failure cases |

Existing `AgentEvent`, `ToolInvocation`, `ModelInvocation`, `CostLineItem`, `EvaluationRun`, `TripRecommendation` are reused. Persist real tool durations and errors; retain fixture tags. Account deletion/export must cover newly owned records, not shared public corpus. All trip edits require ownership and CSRF; no cross-user retrieval trace or saved-place leak. SQL queries scope to authenticated user, including joins; never trust client user IDs. Shared corpus access default authenticated; safe read-only landing excerpts can be bundled static. Limit query length (e.g. 1000 chars), list page sizes, comparison to 3, hop depth ≤2, rate/concurrency; validate slug and UUID. Reject arbitrary remote URLs in public APIs to prevent SSRF. No secrets, raw private prompts, or full sensitive provider payloads in logs.

## API contract (all paths prefixed `/api/v1`)

| Method/path | Request/response intent |
|---|---|
| GET /destinations | paginated q, region, category, limit, cursor; canonical summary + cover credit + coverage |
| GET /destinations/{slug} | guide sections, facts, attraction summaries, images, estimates, citations, as_of, snapshot |
| GET /destinations/{slug}/attractions | paginated category-filtered POIs with verified coordinates |
| POST /discovery/search | query, optional constraints/filters, page size; normalized intent, ranked destinations, matched/unknown preferences, evidence, retrieval_run_id |
| POST /destinations/compare | 2–3 canonical IDs, preferences; aligned dimensions, missing-data flags, evidence |
| POST /destinations/{slug}/ask | query, optional conversation context; answer claims, citations, insufficient_evidence flag |
| GET /destinations/{slug}/graph | bounded subgraph, nodes/edges and evidence refs, snapshot |
| GET/POST /saved-destinations | list or idempotently save canonical ID |
| DELETE /saved-destinations/{id} | unsave user's record |
| GET /knowledge/sources/{id} | authorized exact excerpt/source, revision, section, attribution |
| GET /knowledge/stats | corpus and index health, counts, coverage, snapshot, capabilities |
| POST /retrieval/search | strategy, query, filters, top_k; trace and selected evidence |
| GET /retrieval/runs/{id} | owner-only stage details, ranks, scores and measured timings |
| POST /evaluations/retrieval | bounded local benchmark config; existing evaluation run pattern |
| existing trips/runs endpoints | additive destination_id, snapshot_id, parent run, evidence, generation provenance |
| PATCH /trips/{id}/activities or existing edit route | typed changes with expected version, atomic validation and new version |
| POST /trips/{id}/replan-day | day number, constraints, expected version; linked run and new version on success |

Route order: register static `compare`/search routes before dynamic slug route if method/path would conflict. Match actual API conventions and use consistent errors (401, 403/404 ownership, 409 stale version, 422 validation, 429 limit, 503 missing snapshot/provider). Do not expose ingestion/activation as arbitrary-user endpoints. Use local CLI.

### Example discovery contract (illustrative, IDs not real)

```json
{
  "query": "quiet hill towns with waterfalls",
  "filters": {"region": "Meghalaya", "duration_days": 5, "budget_inr": 25000, "travelers": 2, "origin": "Kolkata"},
  "strategy": "hybrid_rerank"
}
```

```json
{
  "snapshot_id": "india-v1",
  "retrieval_run_id": "<uuid>",
  "intent": {"interests": ["waterfalls", "hills"], "preferences": ["quiet"]},
  "results": [{"destination_id": "<id>", "slug": "sohra", "name": "Sohra", "matched_preferences": ["waterfalls"], "unknown_preferences": ["crowd_level", "budget_fit"], "evidence_ids": ["<citation-id>"], "rank": 1}],
  "generation_mode": "deterministic_evidence",
  "warnings": [], "insufficient_evidence": false
}
```

### Citation and itinerary contract

Citation: `id, source_id, chunk_id, snapshot_id, title, section_path, excerpt, revision_url, license, fetched_at`. Each generated claim contains one or more existing citation IDs or explicit `verification_status=estimate|user_input|unknown`. Activity contains canonical `attraction_id` if factual POI, `title`, `day_number`, `start_minutes`, `duration_minutes`, nullable geo, cost range + basis, citation IDs, `verification_status`. LLM returns only identifiers and structured choices; backend resolves display fields and calculates costs from stored records. Validate ID membership against retrieved candidates and allowed sources, not merely ID existence. Unknown facts cannot pass as verified.

## Acceptance

Migration tested on fresh/legacy DB; no data loss; API tests validate payloads, ownership, CSRF, pagination, missing snapshot, concurrent edit conflicts and backward-compatible old trips. OpenAPI docs updated. Frontend typed clients match contracts; no duplicated handwritten schema drifting from backend. Citation links work after snapshot refresh and trip restore.
