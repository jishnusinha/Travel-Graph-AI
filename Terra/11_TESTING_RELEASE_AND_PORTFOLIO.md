# 11 — Tests, local release, security and portfolio

## Testing strategy

Preserve all existing tests and document baseline failures separately. Use deterministic fixtures for unit tests and a real licensed snapshot + pinned local model for offline integration tests. Mock HTTP/provider calls for error tests; do not confuse mocks with measured retrieval. Avoid network calls during ordinary tests. Separate `unit`, `integration`, `offline_smoke`, `live_optional`, `e2e` markers. Test on Windows when available; if actual Windows execution unavailable, state it, do not fabricate verification.

| Suite | Required coverage |
|---|---|
| Backend unit | adapters, normalization, chunk IDs, embeddings/index validation, FTS, fusion, rerank, graph traversal, citations, cost, route, validation |
| DB/API | migrations fresh/legacy, snapshot activation, ownership, CSRF, validation, rate limits, edit version conflicts, deletion/export, historical citation resolution |
| Graph | fanout barrier, discovery clarification, grounded live output contract, deterministic offline plan, retry changes, unresolved constraints, provider failure, cancel, trace and replay |
| Frontend | route/auth guards, search filters, cards, source drawer, stale search results, map fallback, comparison, budget, trip editing, replay and metrics labels |
| E2E | visitor→auth→search→details→save→plan→inspect→reopen; compare; invalid request; replan one day/restore; old catalog scenario; mobile; account isolation |
| Offline smoke | network disconnected after setup, real local weights, corpus, images, local map, retrieval and planning; no CDN requests |
| Security | prompt injection in corpus, unsafe URL/excerpt, upload limits, secret handling, SSRF prevention, cross-user read/write attempts, no runtime DB in Git |

Use actual assertions for evidence links and plan contents, not only HTTP 200 or screenshots. Validate model outputs with Pydantic and meaningful error tests. Record exact commands, exit codes and counts. Browser visual checks at desktop/tablet/mobile; inspect screenshots and correct major defects. No claims of pixel perfection or full accessibility compliance without audit.

## Developer commands (Windows-first)

Retain `scripts/setup.ps1`, `dev.ps1`, `seed.ps1`, `test.ps1`, `reset-demo.ps1`. Extend setup to create venv/install pinned deps, verify FTS5, migrate (backup existing DB), seed catalog fixtures, prepare/download verified knowledge snapshot, cache models, validate hashes and run smoke. Allow explicit `-CatalogOnly` fallback and `-Offline` mode that checks existing artifacts. Do not download model weights in tests or normal server startup. Add ingest/build-index/evaluate scripts and a `doctor.ps1` or equivalent status command for dependencies, model cache, corpus status and local ports. Scripts use repo-relative paths, quote spaces, propagate failures, and avoid requiring admin rights. Reset command remains confirmation-gated and cannot silently remove user data or shared snapshots.

Expected commands after implementation (adapt to actual scripts and document):

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
.\scripts\test.ps1
.\scripts\evaluate-rag.ps1 -Snapshot india-v1
```

Provide exact local frontend/backend ports from config; current baseline 5173/8000. Use optional live mode only when user explicitly configures `.env` with key and model. Never request keys in chat or add them to tracked files. Keep demo accounts local-only. In production, require strong session secret, secure cookies, no demo seed accounts and restricted CORS; document local-first release is not a production security audit.

## Release gates

- G0: baseline captured; user changes safe; runtime artifacts ignored; migration strategy verified.
- G1: real corpus and source credits, deterministic snapshot and offline readiness checks.
- G2: measured keyword/dense/hybrid/rerank with citations, tests and real traces.
- G3: complete end-to-end P0 discovery→planning→saved itinerary→studio, legacy demo regression.
- G4: P1 maps/comparison/wishlist/budget/edit/versioning works on desktop/mobile, optional tools degrade honestly.
- G5: P2 graph-enhanced retrieval and visual search/personalization implemented and measured, or documented external blocker with no fake UI.
- G6: evaluation report, passing tests/build, screenshots, offline smoke and documentation. List any unmet gates as incomplete; do not claim completion.

## Documentation deliverables

Update root README with product architecture, setup, actual data coverage, mode matrix, screenshots, demo walkthrough, limitations and license notices. Add `docs/TERRA_INTEGRATION_PLAN.md` (link to specs), `docs/DATA_SOURCES.md`, `docs/DATA_LICENSES.md`, `docs/RAG_ARCHITECTURE.md`, `docs/GRAPH_RAG_ARCHITECTURE.md`, `docs/API_CONTRACTS.md`, `docs/EVALUATION_REPORT.md`, `docs/terra-visual-qa.md`, update `docs/AGENT-HANDOFF.md`. Include architecture diagrams (Mermaid), snapshot/config versions, actual benchmarks and reproducible commands. Document which optional services require network and which data isn't current. Do not publish database contents or user prompts.

## Portfolio demo (5–7 minutes)

1. Landing → search “quiet hills with waterfalls and culture” (no destination).
2. Show ranked candidates, open source drawer and compare places; explain unknown cost/crowd information.
3. Select destination, confirm origin/dates/budget/travelers, run actual LangGraph planner.
4. Inspect itinerary citations, budget ranges, map and validation; save and replan one day.
5. Open Agent Studio and replay retrieval stages; compare keyword/dense/hybrid/rerank/graph in playground.
6. Show measured evaluation on held-out queries and cost provenance. Explain why local SQLite/FTS and exact dense search were chosen; limitations and next steps.

Resume wording only after implementation: “Built an offline-capable source-grounded travel discovery and multi-agent planning platform with hybrid retrieval, validated structured itineraries and persisted execution traces.” Add measured counts and improvements only from actual reports. Never claim real-world accuracy or savings without evidence.
