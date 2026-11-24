# Terra × TravelGraph AI — implementation pack

**Target repository:** `jishnusinha/Travel-Graph-AI`, baseline branch `master`.
**Product:** Terra — Powered by TravelGraph AI. One application, one authentication system, one trip store, two complementary experiences.

## How to use this pack

1. Extract the supplied ZIP into the repository root, so `Terra/00_README.md` exists alongside `backend/`, `frontend/`, `scripts/` and `MOCK-UP/`.
2. Open the repository root in Cursor. Use Agent mode, with terminal and file editing available. Ensure working changes are saved before starting. Do not paste API keys into the prompt.
3. Paste the contents of `Terra/CURSOR_MASTER_PROMPT.md` into Cursor Agent. It will read the remaining files in order. The plans are specifications, not implementation code.
4. Keep `Terra/` as the source of truth for this integration. The agent maintains `Terra/IMPLEMENTATION_STATUS.md` and implementation documentation in `docs/`. If context runs out, use the continuation prompt in the master prompt file.

## Execution order

| File | Workstream | Dependency |
|---|---|---|
| 01_PRODUCT_AND_SCOPE.md | Product contract, flows, scope and design decisions | None |
| 02_BASELINE_AND_ARCHITECTURE.md | Audit, compatibility, architecture and local modes | 01 |
| 03_DATA_AND_INGESTION.md | Sources, canonical registry, ingestion and snapshots | 02 |
| 04_DATABASE_AND_API.md | Schema, migrations, contracts and authorization | 02–03 |
| 05_HYBRID_RAG.md | Indexing, retrieval, reranking, citations | 03–04 |
| 06_LANGGRAPH_AND_PLANNER.md | Agent integration, validated plans and real telemetry | 04–05 |
| 07_TERRA_UI.md | Public landing, discovery, destination details, workspace | 04–05; wire to 06 |
| 08_MAPS_BUDGET_AND_TRIP_EDITING.md | Map explorer, comparison, saved places, plan refinement | 06–07 |
| 09_GRAPHRAG_AND_VISUAL_DISCOVERY.md | Entity graph, multi-hop retrieval, image discovery | 03–08 |
| 10_INTELLIGENCE_AND_EVALUATION.md | Studio, retrieval lab, benchmark, costs and replay | 05–09 |
| 11_TESTING_RELEASE_AND_PORTFOLIO.md | Quality gates, Windows setup, documentation and demo | All |
| 12_EXECUTION_BACKLOG.md | Work packages, gates and scope sequencing | All |
| IMPLEMENTATION_STATUS.md | Mutable checkpoint for Agent | All |
| CURSOR_MASTER_PROMPT.md | Paste into Cursor | All |

Plans define a complete target, not a claim of existing implementation. P0 is a working interview-ready vertical slice; P1 and P2 must follow in order, not be silently omitted. Live providers are optional and must never prevent the offline release. All requirements marked optional concern external-service availability or clearly identified enhancements, not the core workflow.

## Precedence

Current user instructions and these Terra plans supersede conflicting product requirements from the old `TRAVELGRAPH_AI_CURSOR_MASTER_PROMPT.md`. Preserve its local-first, Windows, security, testing and existing functionality constraints. Inspect the real working tree first: the repo may have changed since the plans were authored. The repo's existing mockups remain read-only. Do not repeat earlier work merely because a planned file name differs from the actual code.
