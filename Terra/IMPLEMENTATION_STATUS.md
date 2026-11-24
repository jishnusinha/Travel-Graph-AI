# Terra integration — implementation status

Updated 2026-11-24 after implementation on local branch `feat/terra-integration` (not pushed). Base commit `6d725ff`.

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
| T02 | Partial | Wikivoyage fetch of the 50-place registry: 42 pages stored with CC BY-SA 4.0 and revision ids. 8 titles returned missing. Goa revision `5407841` | Wikipedia, OSM, Commons, weather not fetched |
| T03 | Partial | Active snapshot `india-v1`: 42 documents, 525 chunks, 289 attractions, 0 images. FTS5 present. Embedding kind `unavailable` | Local embedding weights were not downloaded |
| T04 | Partial | Keyword/FTS works on `india-v1`. Hybrid requests record `dense_unavailable` and `fell_back_to_keyword`. Rerank records `rerank_unavailable`. RRF and a labeled test-double dense path are unit-tested | Do not describe the live snapshot as hybrid or reranked |
| T05 | Done for current API | Discovery, detail, compare, save, ask, stats. Auth tests in `test_terra_api.py` use the synthetic fixture | — |
| T06 | Done | Catalog Goa path unchanged under `KNOWLEDGE_MODE=catalog`. RAG mode on the real snapshot produced a Sohra plan with `generation_mode=deterministic_evidence`, cost provenance `local_retrieval_no_llm`, total USD 0, and activity titles taken from the Cherrapunji article: Seven Sister Falls, Nohkalikai Falls, Elephant Falls, Cherrapunji Eco Park, Nohsngithiang Falls. Budget `verification_status=unknown` | — |
| T07 | Partial | Retrieval runs and hits are stored. RAG tool rows use `knowledge.retrieve` and `local-retrieval`. Existing SSE/replay still serve agent events | Retrieval playground is a page, not a pixel-verified studio |
| T08 | Partial | Landing, Explore, destination, compare, saved, schematic map, retrieval and knowledge routes. Typecheck passed | No browser screenshot pass in this session |
| T09 | Partial | Keyword evaluation on `india-v1`: 2 measured, 0 skipped, hit@3 **0.5**. `coast-beaches` ranked Goa, Kerala Backwaters, Mysuru (hit). `waterfalls-hills` ranked Shillong, Munnar, Rishikesh (miss; expected Sohra). Embedding kind `unavailable` | Only two reviewed cases. Not a hybrid score |
| T10 | Partial | Registry has 50 candidates. Fetch: 42 ok, 8 missing English Wikivoyage pages (Dawki, Jowai, Nongriat, Mawsynram, Zuluk, Mechuka, Dzükou Valley, Mokokchung). Rebuild: **42 documents, 525 chunks, 289 attractions**, 0 images | Those 8 pages returned `missing`. No coordinates were invented for new places |
| T11 | Partial | Compare, save, schematic map. No offline tile pack | Map is not a road map |
| T12 | Partial | RAG refuses to invent prices. Network tools stay off | No OSRM/Open-Meteo calls |
| T13 | Partial | `POST /trips/{id}/replan-day` keeps other days and returns 409 on a stale version. `POST /trips/{id}/activities/reorder` swaps a neighbor and stores a new version. Trip detail has print, up/down, and replan-this-day. `tests/test_trip_edits.py` passed | Drag-and-drop and a dedicated print stylesheet were not added |
| T14 | Partial | `located_in` and `within_80km_straight_line` edges with method labels. Bounded BFS helper tested | Edges are not a full curated graph |
| T15 | Partial | `/intelligence/knowledge` renders stored edges for Sohra when present | — |
| T16 | Partial | `POST /discovery/visual` returns 503. Personalization requires explicit consent and was API-tested | No image model |
| T17 | Partial | The two-case keyword benchmark above is the only scored table. It is not a strategy comparison | Hybrid and rerank were not measured because no model is installed |
| T18 | Partial | `docs/TERRA.md`, `docs/DATA_SOURCES.md`, `docs/DATA_LICENSES.md`, PowerShell ingest scripts | Desktop/mobile visual QA not run |

## Measured retrieval on `india-v1`

Queried on this machine against the imported Wikivoyage extracts. Strategy requested `hybrid_rerank`. Applied strategy `keyword`. Warnings: `dense_unavailable`, `fell_back_to_keyword`, `rerank_unavailable`.

- `quiet hills and waterfalls` top destinations: Shillong, Munnar, Rishikesh, Udaipur, Kerala Backwaters.
- `Nohkalikai` top destination: Sohra.

These are keyword ranks, not semantic scores.

## Decisions

- 2026-11-24: Keep `KNOWLEDGE_MODE` default `catalog` in code when unset so existing installs do not change. `.env.example` sets `rag` for new setup. Local `.env` was created from that example and omits `DATABASE_URL` so the absolute `data/travelgraph.sqlite` path is used. The example file still has the previous relative URL.
- 2026-11-24: Dense search uses fastembed or sentence-transformers only. If neither model can be opened, the trace says dense is unavailable. Tests use `TestEmbedder` with `kind=test_double`, and production `get_embedder()` does not return it.
- 2026-11-24: Google Fonts links were removed. UI uses Segoe UI and Palatino.

## Browser check on 2026-11-24

Local Vite at `http://localhost:5173` and FastAPI at `http://127.0.0.1:8000`.

- Landing renders the editorial page and lists Wikivoyage opening paragraphs for Darjeeling, Gangtok, Goa, Jaipur, Kerala Backwaters, Manali, Munnar, and Pelling.
- Signed in with the local demo account. The first login landed on the dashboard because `PublicOnlyRoute` replaced the post-login navigation. That route now prefers a stashed Terra query, then the requested `from` path. This fix was not re-tested in the browser after the edit.
- Explore search for “quiet hills and waterfalls for five days” returned Shillong, Sohra, Rishikesh, Jaipur, Munnar, and Kerala Backwaters. The page showed snapshot `india-v1`, strategy `keyword`, vectors `unavailable`, and warnings `dense_unavailable`, `fell_back_to_keyword`, `rerank_unavailable`.
- The Sohra page shows the Cherrapunji opening paragraph, approximate centroid coordinates, “No named attractions were ingested”, “No stored cost estimate”, and the CC BY-SA 4.0 permalink `https://en.wikivoyage.org/w/index.php?title=Cherrapunji&oldid=5397462`.
- A narrow viewport hid the Explore search button behind the mobile nav. Desktop width showed the sidebar and the search.
- Mobile layout, compare, save, map, plan-from-destination, studio, replay, and evaluation screens were not exercised in the browser.

## Retrieval benchmark on 2026-11-24

Command: `python -m app.ingestion.cli evaluate --strategy keyword` against active snapshot `india-v1`.

- Embedding kind: `unavailable`.
- `waterfalls-hills` hit@3 false. Top 3: Shillong, Munnar, Rishikesh. The reviewed label is still Sohra.
- `coast-beaches` hit@3 true. Top 3: Goa, Kerala Backwaters, Mysuru.
- hit@3 across the two measured cases: 0.5. No cases were skipped.

Sohra attractions now stored from text that occurs in the Cherrapunji extract, category `mentioned_in_text`, coordinates unknown: Elephant Falls, Cherrapunji Eco Park, Nohsngithiang Falls, Seven Sister Falls, Seven Sisters Falls, Nohkalikai Falls, Saimika Park.

## Latest checkpoint

Next: install a local embedding model and cross-encoder, rebuild vectors, then browser-check compare, save, the schematic map, a generated trip, and Agent Studio. Do not describe `india-v1` as hybrid or reranked, and do not treat the eight missing Wikivoyage pages as ingested.
