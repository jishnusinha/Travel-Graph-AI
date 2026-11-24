# 02 — Baseline, architecture and operating modes

## Observed baseline (verify again before editing)

Repository inspection showed React/TS/Vite/Tailwind, React Router, React Flow, Recharts, FastAPI, SQLAlchemy/SQLite/Alembic, LangGraph and session auth. Existing relevant files:

- `backend/app/graph/{state,workflow,nodes}.py`: supervisor → fanout → destination/transport/accommodation → barrier → itinerary → validator → aggregator, retry loop.
- `backend/app/providers/{catalog,llm}.py`: local sample catalog and demo/OpenAI provider. Several agents call `complete_json` but ignore results. Existing 5-day Goa itinerary is special-cased. Preserve in catalog mode, not RAG mode.
- `backend/app/services/{run_executor,trip_service,evaluation,benchmark,accounting,run_views}.py`: run execution and persistence; current executor assigns catalog telemetry and demo costs; evaluator includes heuristic preference score. Upgrade, don't replace APIs wholesale.
- `backend/app/models/entities.py`, `backend/alembic/versions/0001_initial_schema.py`, `backend/app/api/router.py`.
- `frontend/src/App.tsx`, `components/layout/nav.ts`, `components/studio/`, `hooks/`, `lib/{api,types,agents,timeline}.ts`, existing trip and analytics pages.
- `docs/AGENT-HANDOFF.md` reports 62 backend / 26 frontend tests passing and a build; these are historical, not freshly verified. `MOCK-UP/` contains 21 references. Read actual docs and code, not guessed paths.
- Git tree had `data/travelgraph.sqlite-wal` and `data/travelgraph.sqlite-shm` tracked. Treat as potentially sensitive runtime files; do not dump contents or commit new DBs. Add ignore rules for `*.sqlite-wal`, `*.sqlite-shm`, `*.db-wal`, `*.db-shm`, checkpoints, raw cache, local model/index caches. Remove tracked runtime files from index without deleting user's working DB; document history exposure and advise owner review/rotation if needed. No history rewrite.

## Phase 0 audit

Record working tree status, current commit, branch, installed versions and exact baseline tests in `Terra/IMPLEMENTATION_STATUS.md`. Never discard user changes. If clean and permitted, create `feat/terra-integration` locally; do not push, merge, or force-reset without user authorization. If branch creation is blocked, note it and continue safely. Use `scripts/test.ps1`, inspect test fixtures, setup/start scripts, route matrix, env and actual migrations. Capture baseline desktop/mobile screenshots where browser tooling exists. Back up local DB before migration; do not reset user DB. Fix preexisting blockers separately or record them. Preserve auth, CSRF, password reset and cross-user access restrictions.

## Architecture decisions

- One FastAPI `/api/v1` service and one Vite frontend; existing SQLite is primary transactional data store. New corpus tables in same SQLAlchemy DB for initial release; immutable snapshot artifacts under `data/knowledge/`. Keep FTS and vector indexes versioned together. No required PostgreSQL, Docker, Redis, Neo4j or hosted services.
- Use **SQLite FTS5/BM25 + exact NumPy cosine search** over normalized float32 embeddings as the default for small corpus (3k–20k chunks); no vector server or local Qdrant locking risk. Define `DenseIndex` protocol so Qdrant local/server is a later optional adapter if benchmark justifies it. Use `sentence-transformers` or equivalent compact local model (default `BAAI/bge-small-en-v1.5`); pin tested package and model revisions. Use compact cross-encoder e.g. `cross-encoder/ms-marco-MiniLM-L-6-v2`, verify license and model availability; pin revision. Models cached at install and opened in offline mode at runtime; no silent random/hash embeddings masquerading as semantic search.
- Local relational knowledge graph via canonical entities/edges + bounded SQL/BFS (NetworkX optional for offline diagnostics). React Flow renders the entity graph; separate from workflow graph.
- Reuse existing LangGraph StateGraph; implement typed retrieval, provider, evidence, validation services independent of graph and route handlers. Use Pydantic for shared output contracts and TS types generated from or tested against OpenAPI.
- Reuse current authentication, CSRF client, SSE, DB session conventions, trip versioning, accounting and dark studio. Do not share async SQLAlchemy session concurrently across parallel nodes. CPU model inference goes through bounded thread worker/semaphore; avoid blocking ASGI loop and unbounded jobs.
- Runtime dependencies: first install can download weights, snapshot, photos and offline map bundle; document exact downloads, hashes and licensing. At runtime no hidden external requests in local mode, including remote fonts, CDN scripts, images or map tiles. Online adapters are opt-in and independent of AI mode.

## Configuration contract

Retain `AI_MODE=demo|openai`. Introduce `KNOWLEDGE_MODE=catalog|rag` (new setup default `rag`, explicit compatibility fallback `catalog`; old configurations without snapshot must show honest actionable status). Add:

```dotenv
AI_MODE=demo
KNOWLEDGE_MODE=rag
KNOWLEDGE_SNAPSHOT=india-v1
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
EMBEDDING_MODEL_REVISION=
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANK_MODEL_REVISION=
RETRIEVAL_STRATEGY=hybrid_rerank
RETRIEVAL_TOP_K=30
RERANK_TOP_K=8
GRAPH_MAX_HOPS=2
ALLOW_NETWORK_TOOLS=false
MAP_MODE=offline
OPENAI_API_KEY=
OPENAI_MODEL=
```

Choose and document actual revision values after testing. Settings validated at startup; invalid combinations fail with actionable instructions, not mysterious fallback. Keep OpenAI keys backend-only. Three workflows: catalog+demo (legacy fixture); rag+demo (actual local retrieval, deterministic evidence-based composition, no LLM); rag+openai (actual local retrieval, validated live generation). If catalog+openai remains supported, explicitly label it catalog. If models/snapshot unavailable, provide status and optional explicit keyword-only degraded search, or clearly labeled catalog mode; do not claim hybrid ran. Model calls cannot silently succeed using demo provider when live credentials fail.

## Proposed package boundaries

`app/ingestion` adapters and CLI; `app/rag` query, embeddings, index, retrievers, fusion, rerank, citations; `app/knowledge` entities/relationships/traversal; `app/services` discovery, planner tools, traces and budgets; `app/api` new route groups; `app/schemas` contracts. Use existing `app/models` conventions and additive Alembic migrations. Frontend feature modules under existing `pages`/`components` and typed `lib`/`hooks`. `data/knowledge/{manifests,snapshots,raw,processed,indexes,models}`; only reviewed redistributable artifacts and small manifests in Git. Keep large artifacts out of Git; distribute via documented release assets or deterministic setup download/build. Do not claim assets published unless actually published.
