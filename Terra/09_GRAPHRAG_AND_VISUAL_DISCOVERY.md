# 09 — Graph-enhanced retrieval, knowledge explorer and image discovery

Implement only after measured hybrid RAG baseline. Do not confuse LangGraph orchestration with GraphRAG. No required graph server. SQLite adjacency tables and bounded traversal are sufficient; React Flow already available for visualization.

## Ontology and extraction

Entity types: `Destination`, `Region`, `Attraction`, `Activity`, `Culture`, `Season`, `TransportHub`, `Document`. Stable IDs reuse canonical registry/POI records; aliases normalized and disambiguated by region/type/external ID. Edge predicates: `LOCATED_IN`, `HAS_ATTRACTION`, `OFFERS_ACTIVITY`, `HAS_CULTURAL_CONTEXT`, `SUITABLE_SEASON` (only sourced), `CONNECTED_TO` (transport evidence), `NEAR` (defined distance rule with method), `MENTIONED_IN`. Store snapshot, edge direction, source chunk/structured record, extraction method, confidence/status. Never infer proximity as actual transport connectivity or entity identity. Rules from OSM/Wikidata and explicit source text first. Optional LLM extraction returns candidate triples with evidence references, validated against allowed schema and source support; unverified edges excluded from retrieval. No invented facts. Build graph version in snapshot, idempotent and reproducible. De-duplicate edges, keep multiple source provenance where relevant.

## Graph retrieval algorithm

1. Resolve query mentions against aliases/external IDs; fallback to top retrieved chunk entity IDs. Start with same filters as hybrid search.
2. Traverse 1–2 hops using predicate allowlist and bounded fanout (e.g. 20 neighbors/node, 100 nodes total), avoid cycles, exclude unrelated regions if hard filter, penalize generic hub nodes. Record path, edge IDs and evidence.
3. Map related entities and paths back to real evidence chunks. Retrieve/score those chunks and fuse with hybrid ranking using a separately documented rank contribution; rerank with query and bounded context. Dedup chunks, retain path provenance. Graph path must link to textual/structured evidence, not be treated as unquestionable proof.
4. Return trace with seeds, selected edges, expansion count, path, added hits, relevance before/after. Support strategy flag `graph_hybrid`; compare to `hybrid_rerank` using identical corpus and query sets. Disable graph augmentation when no valid edges; report it. Do not claim it improves all queries.

Example multi-hop query: places in a region near a named city that have waterfall attractions and culture. Gold labels are manually verified entity/path/source IDs. Test constraints and graph-only false positives; measure path accuracy and retrieval gains/losses.

## Knowledge Explorer UI

`/intelligence/knowledge`: corpus inventory, snapshot/health and license coverage, destination/entity search, bounded subgraph React Flow with distinct colors by type, edge labels, selected node/edge inspector and source excerpt drawer. Filter type/predicate, expand selected node within bounds, reset/fit/pan/zoom, mobile drawer. No force simulation that locks UI; accessible list/table alternative. Distinct from agent execution graph and visual design. For discovery details optional mini “related places” graph with actual provenance. No invented graph nodes for visual balance.

## Visual destination discovery (P2)

Use licensed local destination images already in corpus. Optional pinned CLIP-compatible model (e.g. `openai/clip-vit-base-patch32`, verify license and package availability), local cached weights. Embed images offline, normalize vectors, persist model/revision and image IDs. Add image query endpoint (multipart, authenticated, size/dimension/MIME limits, Pillow decode, decompression-bomb guard, strip EXIF); never execute uploaded files, do not persist user uploads by default, delete temp data, no external upload. Compare query embedding with actual indexed image vectors, group by destination and dedup near-identical photos. Show retrieved image and destination, similarity score clearly defined, not geographic identification or guarantee. Optional combine image and text scores via rank fusion; cite image source and use text evidence for claims. If weights unavailable, mark feature unavailable with setup instructions. Test invalid file, oversized file, image metadata removal, no retained temp file, relevant image similarity and duplicate bias.

## Consent-based personalization (P2)

Use existing user preferences plus explicitly saved destinations to re-rank soft preferences, not inferred sensitive attributes. Toggle personalization off, explain which explicit preferences contributed, clear data in settings; user filters override profile. No tracking across accounts or hidden location inference. Evaluate cold-start vs personalized on controlled test cases; do not claim recommendation accuracy without measured labels.

## Exit gate

Graph build and retrieval deterministic for fixed snapshot; paths have valid evidence and correct filters; traversal bounds tested. Graph UI displays real data and works with keyboard/list fallback. Benchmark same snapshot hybrid vs graph on held-out multi-hop questions, report measured results even if graph is worse. Image search optional setup supports offline genuine embeddings; if external weight download blocked report feature status and exact blocker, not random similarity.
