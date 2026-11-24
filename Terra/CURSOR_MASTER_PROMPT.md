# CURSOR AGENT — TERRA × TRAVELGRAPH AI MASTER IMPLEMENTATION PROMPT

You are the lead full-stack AI engineer, data engineer, LangGraph engineer, UI designer and QA engineer for the existing Travel-Graph-AI repository currently open in Cursor. Implement **Terra — Powered by TravelGraph AI** as an integrated product, not a separate app and not a rewrite.

## 1. Read the specifications before editing

Read `Terra/00_README.md`, then every numbered plan `Terra/01_*.md` through `Terra/12_*.md`, and `Terra/IMPLEMENTATION_STATUS.md`. Use `12_EXECUTION_BACKLOG.md` as the dependency-ordered work queue. Also read the actual repo README, old `TRAVELGRAPH_AI_CURSOR_MASTER_PROMPT.md`, `docs/AGENT-HANDOFF.md`, existing code, tests, migrations, PowerShell scripts, and actual `MOCK-UP/` references. The Terra specs supersede the old prompt's conflicting product/design choices; retain its security, local-first, Windows and working-feature constraints. Verify the current code rather than assuming the inspected baseline is unchanged.

## 2. Non-negotiable engineering constraints

- Keep existing React/TypeScript/Vite/Tailwind frontend, FastAPI/SQLite/SQLAlchemy/Alembic backend, auth, LangGraph, SSE, trip versions, replay, evaluation and cost views. Preserve all existing features, tests and legacy demo behavior. Do not migrate to Next.js or require Docker, PostgreSQL, Redis, Neo4j or a vector server.
- Terra is the editorial travel workspace; TravelGraph AI is the intelligence engine and existing dark technical workspace. Implement real UI, not full-screen screenshots, static mockups or inert controls. Keep `MOCK-UP/` read-only.
- Build a real licensed travel corpus from Wikivoyage, Wikipedia, OpenStreetMap and Wikimedia Commons with revision/source attribution, stable IDs, section-aware chunks, snapshot manifest and offline reproducibility. No fabricated guides, citations, photographs or data counts. Use documented estimates only, never live booking claims. Current travel conditions are unknown unless verified.
- Implement actual local semantic embeddings, SQLite FTS5/BM25, dense search, RRF, cross-encoder reranking and citations. Build graph-enhanced retrieval after hybrid baseline; actual graph relationships must have evidence. Distinguish knowledge graph from LangGraph execution graph. Implement local image similarity and personalization per specs.
- Preserve `AI_MODE=demo|openai`, add independent `KNOWLEDGE_MODE=catalog|rag`. New offline RAG uses real retrieval and deterministic evidence-based composition, not simulated LLM output. Live OpenAI mode is explicit, optional, backend-only and must consume validated structured results. No paid service calls or API keys required for offline setup. If a model/source cannot be fetched, label the failure/degraded mode; never substitute fake embeddings, telemetry, citations or metrics.
- Extend existing agent workflow with destination discovery/clarification, grounded research, actual structured planning, basis-aware budget calculation, validated citations, geographic constraints, bounded meaningful replanning and saved versions. No arbitrary Goa fallback, fake route, exact unverified costs or success status when hard constraints remain unresolved. Existing catalog fixtures remain isolated and labeled.
- Capture measured retrieval stages and provider usage at actual service boundaries, persist trace events, stream and replay without rerunning inference. Build RAG Playground, Knowledge Explorer and expand Evaluation Lab with reviewed gold cases, comparable retrieval strategies, actual metrics and honest N/A judge/cost states.
- All new user-owned records must enforce existing ownership and CSRF rules. Treat source text and uploads as untrusted. No secret disclosure, unsafe remote URL fetching, raw private prompt logs or tracked runtime databases. Keep local models, downloaded data and assets licensed and versioned. Inspect tracked SQLite WAL/SHM hygiene without dumping sensitive contents or rewriting history.
- Offline after initial setup means no hidden HTTP calls for model loading, map tiles, fonts, images or planning. Optional routing/weather/live model services must be opt-in. Windows PowerShell remains supported.

## 3. Execution protocol — implement, do not merely plan

Start with T00. Inspect `git status`, branch and commit; protect existing user modifications and database contents. Run baseline tests/build and record actual output. If safe, work on a local `feat/terra-integration` branch; no push, merge, force-reset, history rewrite, destructive data reset or paid actions without explicit user instruction. Do not expose or request secrets. Use migrations on test/copy databases before user DB. Follow T00–T18 in dependency order, working through P0, P1 and P2. Do not stop after scaffolding or a beautiful landing page.

For every package:
1. Read the relevant plans and inspect existing implementation.
2. Implement actual source code, typed contracts, migrations, scripts, UI and tests as appropriate. Reuse working code; avoid redundant frameworks and unnecessary abstractions.
3. Run focused tests and relevant baseline regression, typecheck/build and browser smoke. Fix failures attributable to your changes. Inspect screenshots for visual issues at desktop and mobile widths.
4. Update `Terra/IMPLEMENTATION_STATUS.md` with package state, files changed, exact commands/results, snapshot/model versions, decisions/deviations, gate status, blocker and next action. Update implementation docs and README as work progresses.
5. Continue to the next dependency-ready package. If context or execution limits intervene, stop at a safe checkpoint, leave working state, and give a precise continuation summary. Do not claim that unrun tests passed or blocked work is finished. If an external dependency fails, implement truthful error handling and proceed with independent work rather than fabricate data or wait for keys.

## 4. Required product demonstration and completion gates

Before declaring completion, verify all applicable gates in `Terra/11_TESTING_RELEASE_AND_PORTFOLIO.md` and `Terra/12_EXECUTION_BACKLOG.md`. Demonstrate: public landing → sign in → destination-free semantic discovery → citations → compare/save → select destination → generate real offline grounded plan → budget/map → edit/replan and restore → inspect agent and retrieval traces → replay → compare retrieval strategies on reviewed benchmark. Verify original catalog demo and existing auth/studio/cost/evaluation routes remain functional. Show actual corpus counts, measured metrics and limitations. Complete all P0/P1/P2 deliverables or list exact unmet requirements and external blockers without pretending they work.

At handoff report: actual implemented functionality, changed files, local branch/commit status, commands run and results, how to start and test on Windows, current offline snapshot/model readiness, measured evaluation, screenshots, and remaining blockers. Do not fabricate completion or publish externally. Begin now by reading the specs and performing the baseline audit, then implement T00 onward.

---

## Continuation prompt (use in a new Cursor Agent chat only if needed)

Read `Terra/00_README.md`, `Terra/CURSOR_MASTER_PROMPT.md`, all numbered specs and `Terra/IMPLEMENTATION_STATUS.md`. Inspect current git status/diff and actual code; verify the last completed gate with focused tests. Resume from the first incomplete dependency-ready package in `Terra/12_EXECUTION_BACKLOG.md`. Preserve all prior working changes, do not rebuild completed work, update the status file with real evidence after each package, and continue through the remaining P0/P1/P2 gates. No destructive operations, push, fake data/metrics or paid calls. Report actual results and blockers.
