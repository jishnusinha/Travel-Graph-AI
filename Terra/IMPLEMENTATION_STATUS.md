# Terra integration — implementation status

Updated 2026-11-24 after the critical-correction pass on local branch `feat/terra-integration` (not pushed, not merged). Base commit `6d725ff`.

## Critical corrections (2026-11-24)

`data/travelgraph.sqlite.bak-terra` was tracked. It contains one password hash and one session row (token hash and CSRF token). It was removed from the index with `git rm --cached` and the working file was kept. History was not rewritten. `.gitignore` now ignores sqlite/db files and their suffixes under `data/`. The deletion is staged and has not been committed.

`python -m pytest -q` in `backend/` after the correction: **102 passed** in 29.50s.

Local models were installed with `fastembed` 0.9.1 (ONNX). Torch and `sentence-transformers` are not installed. The cross-encoder used at runtime is the ONNX export `Xenova/ms-marco-MiniLM-L-6-v2` of the configured MiniLM model. Manifest `data/knowledge/models/terra-model-manifest.json` (gitignored):

- Embedding: `BAAI/bge-small-en-v1.5`, kind `fastembed`, dimension 384, weight sha256 prefix `51f1bd0addd6e859`.
- Reranker: `Xenova/ms-marco-MiniLM-L-6-v2`, kind `fastembed_cross_encoder`.

`scripts/prepare-knowledge.ps1` downloads those models, reads the Wikivoyage cache, rebuilds `india-v1`, and runs `verify-retrieval`. Runtime `ALLOW_MODEL_DOWNLOAD` stays false. Model objects are cached in-process. Discovery, ask, retrieval search, and RAG graph nodes run inference through a two-worker thread pool so the API event loop is not blocked on the encode or rerank call.

Rebuild of `india-v1`: **42 documents, 525 chunks**, embedding kind `fastembed`, model `BAAI/bge-small-en-v1.5`. The same 8 Wikivoyage titles are still missing. Image count is still 0.

`verify-retrieval` on that snapshot reported `failures: []`. Every `Nohkalikai Falls` run applied the strategy that was requested, and the evidence text included Nohkalikai. Applied strategies were `keyword`, `dense`, `hybrid`, and `hybrid_rerank` with no `dense_unavailable`, `fell_back_to_keyword`, or `rerank_unavailable` warnings. Rerank model recorded on those runs: `Xenova/ms-marco-MiniLM-L-6-v2`.

Measured timings on this machine, same process:

- Dense, first query (includes model load): `dense_ms` 2308, total 2341.
- Dense, next query: `dense_ms` 23, total 82.
- Cross-encoder over the fused candidate pool: `rerank_ms` about 5.0–5.8 seconds. That is real CPU time, not a keyword fallback.

Reviewed two-case file, 0 skipped:

| Strategy | hit@3 | waterfalls-hills top 3 | coast-beaches top 3 |
|---|---|---|---|
| keyword | 0.5 | shillong, munnar, rishikesh (miss) | goa, kerala-backwaters, mysuru (hit) |
| dense | 1.0 | sohra, shillong, yuksom (hit) | goa, puducherry, kerala-backwaters (hit) |
| hybrid | 1.0 | sohra, shillong, kalimpong (hit) | goa, kerala-backwaters, puducherry (hit) |
| hybrid_rerank | 1.0 | munnar, shillong, sohra (hit) | goa, puducherry, kerala-backwaters (hit) |

This is two reviewed cases, not a 50-case comparison. Hybrid ranked Sohra first on the waterfall query. Rerank still hit at 3 but ranked Munnar first. Do not describe reranking as an improvement over hybrid from this sample.

RAG plans no longer copy the first retrieved citation onto an unrelated sight. A cited activity title has to occur in that citation's excerpt. OpenAI mode validates structured claims and retries once; rejected output keeps `generation_mode=deterministic_evidence` and `generation_warnings=["openai_output_rejected"]`. Accepted output is `openai_grounded` and does not replace the activity list or invent prices. `AI_MODE` is `demo` here and no API key is configured, so no live OpenAI call was made.

The source-completion work is in the next section. Terra Playwright screenshots were captured at 1440×900 and 390×844 under `docs/screenshots/terra-*.png`. The reviewed retrieval set is 20 cases, not 50.

## Source completion (2026-11-24)

`india-v1` was rebuilt from the local cache with `python -m app.ingestion.cli build --snapshot india-v1 --limit 0`. The build reads Wikipedia, OpenStreetMap, and Commons from cache and does not call those networks. Result: **92 documents** (42 Wikivoyage, 50 Wikipedia), **581 chunks**, embedding kind `fastembed`, **48 images**, **250 cost rows** for 50 destinations, failures `[]`. `python -m pytest -q` in `backend/` after this rebuild: **110 passed**.

The eight places that had no English Wikivoyage page now have a Wikipedia lead, a revision permalink, and a Wikidata QID:

| Place | Wikipedia title | Revision | Coordinates |
|---|---|---|---|
| Dawki | Dawki | 1386947053 | 25.18333333, 92.01666667 |
| Jowai | Jowai | 1384228129 | 25.44215583, 92.19471583 |
| Nongriat | Nongriat | 1376936141 | none on the page |
| Mawsynram | Mawsynram | 1378776545 | 25.29888889, 91.58138889 |
| Zuluk | Dzuluk | 1372114681 | 27.2509908, 88.7750191 |
| Mechuka | Mechuka | 1376421570 | 28.605, 94.12805556 |
| Dzükou Valley | Dzukou Valley | 1369191641 | 25.553329, 94.067065 |
| Mokokchung | Mokokchung | 1377811462 | 26.32, 94.5 |

Dawki's stored lead is 74 characters. It is the article text at that revision, not a generated summary. Nongriat, Dooars, and Mawlynnong have no coordinates on their Wikipedia pages, so those destination rows stay `coordinate_status=unknown`. The registry title for Lava is `Lava, West Bengal` (revision `1376600547`, Q6502159). The bare title `Lava` is the geology article and is not stored.

Commons stores the Wikipedia page image only, and only with CC0, public domain, CC BY, or CC BY-SA. Lolegaon and Mawsynram have no page image, so the snapshot has 48 photographs. Attribution, author, license, and the file page are on each image row. Lava's file is `File:Lava in May, 2025 in Kalimpong, West Bengal 13.jpg`, CC BY 4.0.

OpenStreetMap named-node queries did not yield POIs. The cache has four error records (timeout or HTTP 502 from the public Overpass interpreters) and one successful Manali response with an empty attraction list. Attraction rows with an OSM id: **0**. No coordinates were filled from a failed query.

Editorial bands in `data/knowledge/manifests/cost_ranges.json` are method `editorial_planning_band`, confidence `low`, checked 2026-11-24. They cover accommodation, meals, local travel, attractions, and contingency by destination kind. Intercity transport and road distance are omitted. They are planning envelopes, not quotes.

Attraction names fold case, apostrophes, a leading "the", and a trailing plural. After the rebuild, repeated name keys in the attraction table: **0**. The table has 284 attraction rows. Old duplicate rows were merged and any trip activity pointing at a removed id now points at the kept id.

## Terra UI and map (2026-11-24)

Scoped Terra tokens keep forest / ivory / clay / sage on travel routes without changing the dark studio. Landing uses a full-bleed Commons hero when the snapshot has a licensed file, the editorial headline, a working discovery composer, theme collections, and a snapshot grid with attribution. Explore cards show cover photographs, evidence counts, filters, compare tray, and auto-run a seeded query. Destination pages use a cinematic hero, editorial cost bands, sources, and Plan trip handoff. Dashboard adds a curated Terra strip from `/knowledge/highlights`.

`GET /api/v1/knowledge/media/{slug}` serves files only from `data/knowledge/assets` for destinations in the active snapshot. Path traversal and unknown slugs return 404. Highlights, destination list/detail, and discovery results include a `photo` object with URL and attribution when a file exists.

MapLibre GL renders an offline style with the local simplified India outline at `frontend/public/geo/india-outline.json` and stored destination pins. Selection syncs with a side list. Missing coordinates are listed, not invented. Attribution names the local outline and OSM-derived pin provenance. No public raster tile CDN is used.

Frontend: `npm run typecheck` passed. `npm test` **27 passed**. MapLibre `5.6.0` is a dependency.

## Knowledge explorer and reviewed benchmark (2026-11-24)

`/intelligence/knowledge` now shows corpus inventory (including entity/relationship counts and document license coverage), destination seed selection, hop/predicate filters, entity search, a React Flow bounded subgraph, node/edge inspector with chunk excerpts when present, and an accessible edge list. `GET /knowledge/entities` supports label search. Destination graph walks 1–2 hops with optional predicate filter. `within_80km_straight_line` remains labeled as haversine, not a road.

`data/knowledge/manifests/eval_cases.json` has **20 reviewed cases** for `india-v1` (not 50). Measured hit@3 on this machine, same process, all 20 present in the snapshot:

| Strategy | hit@3 | hits/n | Misses |
|---|---|---|---|
| keyword | 0.9 | 18/20 | waterfalls-hills, dawki-river |
| dense | 0.85 | 17/20 | sikkim-capital, living-root-bridges, dawki-river |
| hybrid | 0.9 | 18/20 | sikkim-capital, dawki-river |
| hybrid_rerank | 1.0 | 20/20 | none |
| graph_hybrid | 0.8 | 16/20 | waterfalls-hills, sikkim-capital, living-root-bridges, dawki-river |

Graph-hybrid did **not** beat hybrid or hybrid_rerank on this set. Snapshot graph size at measurement: **348 entities**, **442 relationships**. Playwright Terra specs under `frontend/e2e/terra-screenshots.spec.ts` passed against a live API+Vite pair. Captured: `terra-landing-desktop.png`, `terra-explore-desktop.png`, `terra-destination-desktop.png`, `terra-map-desktop.png`, `terra-knowledge-desktop.png`, `terra-landing-mobile.png`, `terra-explore-mobile.png`.

## Baseline

- Branch created from clean `master` at `6d725ff`. Terra specs were untracked.
- The full backend suite was not run before edits. After the integration, `python -m pytest -q` in `backend/` reported **89 passed**. A later run, after the lead-excerpt and discovery-summary changes, reported **91 passed** in 21.20s. After day replan, reorder, and the registry expansion, the same command reported **94 passed** in 27.30s.
- After the later Sohra name-from-evidence change, `pytest tests/test_terra_planner.py tests/test_graph.py` reported **21 passed**.
- After lead excerpts and the discovery summary field, `pytest tests/test_terra_api.py tests/test_terra_retrieval.py tests/test_terra_planner.py` reported **17 passed**. `india-v1` was later rebuilt from 42 cached extracts: 525 chunks, 289 attractions, embedding kind `unavailable`.
- Frontend: `npm test` **27 passed**. `npm run typecheck` passed.
- `data/travelgraph.sqlite` was copied to `data/travelgraph.sqlite.bak-terra` before the snapshot import.
- Tracked `data/travelgraph.sqlite-wal` and `data/travelgraph.sqlite-shm` were removed from the index with `git rm --cached` (working files kept, history not rewritten). They were already in git history; review that history separately if those files ever held session data.

## Work package tracker

| ID | Status | Evidence | Blocker / next action |
|---|---|---|---|
| T00 | Done | Branch, gitignore for WAL/SHM and knowledge caches, baseline tests above | — |
| T01 | Done | `0002_terra_knowledge.py`, `upgrade_schema_sync`, registry `data/knowledge/manifests/destinations.json` | Runtime default stays `catalog` when the env var is absent |
| T02 | Partial | Wikivoyage: 42 pages, CC BY-SA 4.0, revision ids. Wikipedia: 50 leads, including the 8 missing Wikivoyage titles, each with a revision id and QID. Commons: 48 licensed page images. OSM adapter is implemented and unit-tested | Public Overpass returned timeouts or HTTP 502. 0 OSM attraction ids stored. Weather is not fetched |
| T03 | Done for the cached corpus | Active snapshot `india-v1`: 92 documents, 581 chunks, 48 images, embedding kind `fastembed`, model `BAAI/bge-small-en-v1.5`, dim 384. 250 editorial cost rows. `prepare-knowledge.ps1` rebuilds it on Windows | Nongriat, Dooars, and Mawlynnong still have no page coordinates. OSM POIs were not available from Overpass |
| T04 | Done on `india-v1` for keyword, dense, hybrid, RRF and cross-encoder | `verify-retrieval` failures empty. Two-case hit@3: keyword 0.5, dense 1.0, hybrid 1.0, hybrid_rerank 1.0. Rerank model `Xenova/ms-marco-MiniLM-L-6-v2` | Two reviewed cases only. Rerank of the candidate pool measured about 5–6 seconds on this CPU |
| T05 | Done for current API | Discovery, detail, compare, save, ask, stats. Auth tests in `test_terra_api.py` use the synthetic fixture | — |
| T06 | Done for offline evidence; OpenAI path tested with a fake provider | Catalog Goa path unchanged. RAG demo plans stay `deterministic_evidence` with cost provenance `local_retrieval_no_llm`. Cited activities must match their excerpt. Rejected model JSON keeps the deterministic plan. A validated fake response becomes `openai_grounded` without adding places | No live OpenAI call: `AI_MODE=demo` and no key is configured |
| T07 | Partial | Retrieval runs and hits are stored. RAG tool rows use `knowledge.retrieve` and `local-retrieval`. Existing SSE/replay still serve agent events | Retrieval playground is a page, not a pixel-verified studio |
| T08 | Partial | Landing hero with real Commons photo, Explore cards with evidence, destination cinematic detail, dashboard curated strip, compare tray. Typecheck passed | Playwright desktop/mobile screenshot pass not run in this session |
| T09 | Partial | 20 reviewed cases measured for five strategies. hybrid_rerank hit@3 1.0; keyword/hybrid 0.9; dense 0.85; graph_hybrid 0.8 | Not 50 cases. Graph did not improve this set |
| T10 | Partial | All 50 registry places are in `india-v1`. The 8 places without Wikivoyage now use their Wikipedia lead. Seven of those eight have Wikipedia page coordinates. Nongriat does not. 48 images. 284 attractions after name-key collapse | Lolegaon and Mawsynram have no Wikipedia page image. OSM contributed no coordinates |
| T11 | Partial | MapLibre offline style with local India outline GeoJSON, stored pins, list sync, missing-coord warning, attribution | No PMTiles pack. Not a road map. No OSRM |
| T12 | Partial | RAG still refuses to invent prices. Each of the 50 destinations has five `editorial_planning_band` rows, confidence `low`. Intercity transport and road distance are not stored | No OSRM or Open-Meteo calls. The bands are not quotes |
| T13 | Partial | `POST /trips/{id}/replan-day` keeps other days and returns 409 on a stale version. `POST /trips/{id}/activities/reorder` swaps a neighbor and stores a new version. Trip detail has print, up/down, and replan-this-day. `tests/test_trip_edits.py` passed | Drag-and-drop and a dedicated print stylesheet were not added |
| T14 | Partial | `located_in` and `within_80km_straight_line` edges with method labels. Bounded BFS helper tested. india-v1: 348 entities, 442 relationships | Edges are rule/haversine based, not a full curated ontology |
| T15 | Partial | Knowledge Explorer: inventory, entity search, React Flow subgraph, inspector with excerpts, list fallback | Multi-hop held-out graph questions beyond the 20-case table are not separate |
| T16 | Partial | `POST /discovery/visual` returns 503. Personalization requires explicit consent and was API-tested | No image model |
| T17 | Partial | 20 reviewed cases, five strategies. hybrid_rerank 1.0; keyword/hybrid 0.9; dense 0.85; graph_hybrid 0.8. See the knowledge-explorer section | Still not 50 cases. Graph_hybrid is worse here |
| T18 | Partial | Docs updated. Terra Playwright desktop+mobile smoke passed; 7 `docs/screenshots/terra-*.png` artifacts written | Full dark-studio visual QA and production clean-machine setup still open |

## Measured retrieval on `india-v1`

The earlier keyword-only trace is superseded by the 2026-11-24 verification above. `hybrid_rerank` is applied when the local models and vectors are present. If either model cannot be opened, the trace still says `dense_unavailable`, `fell_back_to_keyword`, or `rerank_unavailable`, and the applied strategy is not labeled `hybrid_rerank`.

## Decisions

- 2026-11-24: Keep `KNOWLEDGE_MODE` default `catalog` in code when unset so existing installs do not change. `.env.example` sets `rag` for new setup. Local `.env` was created from that example and omits `DATABASE_URL` so the absolute `data/travelgraph.sqlite` path is used. The example file still has the previous relative URL.
- 2026-11-24: Dense search uses fastembed or sentence-transformers only. If neither model can be opened, the trace says dense is unavailable. Tests use `TestEmbedder` with `kind=test_double`, and production `get_embedder()` does not return it.
- 2026-11-24: The installed stack is fastembed ONNX. The configured cross-encoder name `cross-encoder/ms-marco-MiniLM-L-6-v2` is opened as `Xenova/ms-marco-MiniLM-L-6-v2` when sentence-transformers is absent. The trace records the model that actually scored the pairs.
- 2026-11-24: Google Fonts links were removed. UI uses Segoe UI and Palatino.

## Browser check on 2026-11-24

This pass was before the embedding models were installed. The warnings below describe that earlier keyword fallback, not the rebuilt `india-v1` index.

Local Vite at `http://localhost:5173` and FastAPI at `http://127.0.0.1:8000`.

- Landing renders the editorial page and lists Wikivoyage opening paragraphs for Darjeeling, Gangtok, Goa, Jaipur, Kerala Backwaters, Manali, Munnar, and Pelling.
- Signed in with the local demo account. The first login landed on the dashboard because `PublicOnlyRoute` replaced the post-login navigation. That route now prefers a stashed Terra query, then the requested `from` path. This fix was not re-tested in the browser after the edit.
- Explore search for “quiet hills and waterfalls for five days” returned Shillong, Sohra, Rishikesh, Jaipur, Munnar, and Kerala Backwaters. The page showed snapshot `india-v1`, strategy `keyword`, vectors `unavailable`, and warnings `dense_unavailable`, `fell_back_to_keyword`, `rerank_unavailable`.
- The Sohra page shows the Cherrapunji opening paragraph, approximate centroid coordinates, “No named attractions were ingested”, “No stored cost estimate”, and the CC BY-SA 4.0 permalink `https://en.wikivoyage.org/w/index.php?title=Cherrapunji&oldid=5397462`.
- A narrow viewport hid the Explore search button behind the mobile nav. Desktop width showed the sidebar and the search.
- Mobile layout, compare, save, map, plan-from-destination, studio, replay, and evaluation screens were not exercised in the browser.

## Retrieval benchmark on 2026-11-24

The keyword-only numbers below are the earlier run, before vectors existed. The four-strategy table in the critical-corrections section is the current measurement.

Command: `python -m app.ingestion.cli evaluate --strategy keyword` against active snapshot `india-v1`.

- Embedding kind: `unavailable`.
- `waterfalls-hills` hit@3 false. Top 3: Shillong, Munnar, Rishikesh. The reviewed label is still Sohra.
- `coast-beaches` hit@3 true. Top 3: Goa, Kerala Backwaters, Mysuru.
- hit@3 across the two measured cases: 0.5. No cases were skipped.

Sohra attractions now stored from text that occurs in the Cherrapunji extract, category `mentioned_in_text`, coordinates unknown: Elephant Falls, Cherrapunji Eco Park, Nohsngithiang Falls, Seven Sister Falls, Seven Sisters Falls, Nohkalikai Falls, Saimika Park.

## Latest checkpoint

Critical corrections, source completion, Terra UI/map, Knowledge Explorer, a 20-case strategy table, and Terra screenshots are in the working tree and are not committed. Working branch is currently `master` with local modifications. Backend pytest: **112 passed**. `india-v1` has 92 documents, 581 chunks, 48 images, 348 entities, and 442 relationships. hybrid_rerank hit@3 is 1.0 on the 20 reviewed cases; graph_hybrid is 0.8 and is not an improvement. Remaining gaps: expand reviewed cases toward 50 if needed, production clean-machine setup, and optional live OpenAI only when a key exists.
