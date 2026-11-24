# 12 — Dependency-ordered backlog and delivery gates

Use this sequence; complete a vertical slice before visual polish or advanced features. Mark actual status in `IMPLEMENTATION_STATUS.md` after each work package. Do not treat this checklist as implementation. Adapt exact file names to inspected repo and document deviations. Each package includes tests and docs.

| ID | Priority | Work package | Dependency | Exit artifact |
|---|---|---|---|---|
| T00 | P0 | Audit git, docs, routes, scripts, migrations; run baseline tests; protect data and ignore WAL/SHM | — | Baseline record, safe branch/status |
| T01 | P0 | Define config, schemas, canonical registry and migration; verify legacy data | T00 | Migration tests, API contracts |
| T02 | P0 | Source adapters Wikivoyage/Wikipedia/OSM/Commons; cache/normalize/license | T01 | Real source files and manifest |
| T03 | P0 | Chunk, embed, FTS and snapshot build/activation; offline setup | T02 | Verified initial snapshot and model cache |
| T04 | P0 | Keyword/dense/hybrid/RRF/rerank, intent, evidence/citations | T03 | Actual retrieval traces and tests |
| T05 | P0 | Discovery and details API, destination QA, attribution | T04 | Typed API and auth tests |
| T06 | P0 | LangGraph integration, grounded offline/live provider, validation, persistence | T04–05 | Non-Goa real cited plan, legacy tests |
| T07 | P0 | Real events, usage and replay, retrieve inspector | T06 | Saved trace + SSE + replay smoke |
| T08 | P0 | Terra shell, landing, explore, destination detail, dashboard, planner handoff | T05–07 | Responsive real-data vertical slice |
| T09 | P0 | Retrieval playground and initial reviewed benchmark, cost/eval labels | T07–08 | Measured baseline, report and P0 gate |
| T10 | P1 | Expand dataset toward 50 destinations, image curation and quality/coverage | T03–09 | Updated manifest, source credits |
| T11 | P1 | Map/list, offline maps, comparison, saved places | T08 | Map attribution, wishlist E2E |
| T12 | P1 | Basis-aware costs, budget UI, optional routing/weather | T06,T11 | Deterministic totals and honest fallbacks |
| T13 | P1 | Editable itinerary, partial replan, version restore, print/export | T06,T12 | Concurrency and regression E2E |
| T14 | P2 | Provenanced entities/edges, bounded graph traversal, graph strategy | T04,T10 | Graph snapshot, path tests |
| T15 | P2 | Knowledge Explorer, graph traces, multi-hop benchmark | T14 | Actual graph UI and measurements |
| T16 | P2 | Local image similarity and consent-based personalization | T10,T15 | Real model results and privacy tests |
| T17 | ALL | Expanded reviewed benchmark; comparison, cost reconciliation, failure analysis | T09,T13,T15,T16 | Actual JSON/CSV and evaluation report |
| T18 | ALL | Complete desktop/mobile visual QA, offline smoke, security and docs | T17 | Final tests/build, screenshots, handoff |

## Suggested commit boundaries

Use one local integration branch `feat/terra-integration` with small logical commits (baseline/data/rag/planner/ui/maps/graph/eval/release), or dependency-ordered stacked feature branches if user prefers. Do not create many independent divergent branches without integrating dependencies. Never push/merge/reset without explicit user instruction. If Git not available or worktree contains user changes, leave safe changes and report state. Do not commit keys, logs, local DBs, downloaded model weights or unreviewed large content. Review diffs for scope and attribution.

## Working method for Cursor

For each package: read related specs and actual files → implement minimum real working vertical slice → add tests → run focused tests → run relevant regression/build → update status with evidence and blockers → continue. If a package depends on an external unavailable asset, implement honest error handling and tests, record exact missing dependency and move to independent work; do not fabricate data or claim success. If context/tool budget ends, stop at safe checkpoint and provide continuation summary. Do not repeatedly ask for permission for ordinary local code edits authorized by the prompt; destructive changes, external publish, paid calls and secret access are not authorized.
