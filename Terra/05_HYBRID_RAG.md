# 05 — Real retrieval-augmented intelligence

## Core service design

Implement retrieval independently from LangGraph; reuse in discovery, destination Q&A, itinerary agent and evaluation. Suggested typed objects: `SearchIntent`, `RetrievalRequest`, `RetrievalHit`, `Evidence`, `RetrievalTrace`, `DiscoveryResult`, `GroundedAnswer`. `Retriever.search(request, context)` returns evidence and measured stage trace; no hidden network dependency. Separate candidate ranking from generation and persist snapshot ID. Do not require LLM to search locally.

## Query understanding

Use deterministic local extraction for explicit region/place aliases, date/duration, rupee budgets (including `25k`, `₹25,000`), traveler count, origin and taxonomy synonyms. Preserve original query for embeddings. Optional live schema-constrained LLM extraction validated against known values; merge explicit form fields first, then validated parsed fields. Unknown fields remain null. Explicit hard filters (region, known destination, category) are applied consistently to dense and sparse candidates; soft preferences affect ranking, not hard exclusions. Do not filter by budget unless compatible known origin, duration, travelers and estimate basis. Avoid over-filtering when metadata incomplete; report relaxed filters explicitly and never silently relax hard user requirements.

## Indexing

- Use model-specific tokenizer, exact tested model revision, documented query/document prefixes (BGE model usage as required). Batch encode, normalize L2, float32 vectors; store stable row→chunk ID mapping. Validate dimensions/checksum/model identity at load. Build immutable indexes in temp location then atomically activate.
- Exact cosine similarity: matrix-vector dot product on normalized vectors; apply metadata candidate mask, deterministic tie-break by chunk ID. Persist raw similarity, rank and stage. No fake percentage conversion. Cache embeddings keyed by normalized query/model version if bounded and privacy-safe.
- FTS5 with Unicode tokenizer and sanitized tokens/quoted terms; BM25 rank semantics lower is better in SQLite. Treat punctuation/operators safely, bound token count, test query syntax. Retrieve only same snapshot. FTS5 availability check during setup; explicit actionable fallback if unsupported.

## Retrieval strategies

`keyword`, `dense`, `hybrid`, `hybrid_rerank`, `graph_hybrid` (phase 9). Support configuration per benchmark/playground, same corpus and filters. Defaults start at 30 candidates each, fusion pool 40, final evidence 8; tune from measured data.

1. Retrieve top-k sparse and dense in parallel if safe; measure actual times; handle empty results.
2. Reciprocal Rank Fusion: `score(d) = sum(1/(60 + rank_i(d)))` for ranks starting at 1; dedup by stable chunk ID. Rank descending, deterministic ties. Scores across strategies not comparable. Add source diversity and per-destination/section caps without hiding original ranking.
3. Cross-encoder rerank top candidate pool with query/chunk pairs, record raw logits or model-defined scores and before/after ranks. Select final 5–10 evidence chunks constrained by context budget. If reranker unavailable, return explicit hybrid fallback trace; do not label reranked.
4. For discovery, group ranked evidence by destination; use bounded evidence aggregation (e.g. top 3 RRF contributions per destination), diversify top results, apply soft preference coverage using actual tagged or textual evidence. Do not favor destinations merely because they have more documents. Show reason + citations, unknown preferences, coverage warnings. No synthetic “96% match” unless calibrated and defined.
5. For Q&A/itinerary, retrieve destination-specific sections, optionally multiple focused queries (attractions, culture, transport). Neighbor chunks may expand context; keep source boundaries and deduplicate. Determine evidence adequacy via tested rules; calibrate on held-out unanswerables. Empty/weak/contradictory evidence → abstain or explicitly qualify. Distinguish source disagreement and freshness.

## Grounded generation

`AI_MODE=demo` uses deterministic extractive/template composition with actual returned evidence, labeled `deterministic_evidence`. No claim of LLM generation. `AI_MODE=openai` uses existing provider upgraded to typed JSON schema (use supported structured output or strict parse+Pydantic validation) and sends only relevant bounded evidence. Prompt states retrieved text is untrusted data, ignore instructions within documents, no new locations/IDs/citations, acknowledge unknown facts. Use allowlisted candidate identifiers. Validate every returned claim citation against selected evidence; citation membership alone is not entailment, so inspect support and abstain on unsupported claims. Never let LLM calculate final costs, fabricate route geometry or quote ticket prices. Retry malformed output once with validation feedback; if still invalid, fall back to labeled deterministic evidence or report failure. Never silently switch providers.

Example response internal shape:

```json
{"claims":[{"text":"<source-supported statement>","evidence_ids":["<selected-id>"]}],"unknowns":[],"insufficient_evidence":false}
```

Citation resolver loads stored source revision/section/excerpt and license, not a generated URL. Store exact cited excerpt with trip version. Render source chip/side panel from backend data. Sanitize excerpts for HTML and escape Markdown links; no arbitrary script or remote resource fetch. Use safe URL schemes and external link rel attributes.

## Observability and performance

Measure monotonic timing for normalization, embedding, FTS, dense, fusion, rerank, graph expansion, context selection and total. Persist ranks, selected and rejected candidates, configuration/model versions, snapshot, fallback status; mask sensitive input in logs. Avoid logging full prompts by default. Use bounded executor/semaphore for CPU model inference; preload weights once or lazy warmup with readiness status, never download unexpectedly at runtime. Use max query size and top-k limits. Test concurrent searches and memory consumption; record cold/warm separately. No promised latency until measured on actual machine.

## Tests and exit gate

Unit: query parsing, filter precedence, FTS escaping, normalized cosine, stable ties, RRF arithmetic, dedup, rerank order, context truncation, source validation, unknown evidence and injection-like documents. Integration: real pinned local model + actual snapshot with network disabled; keyword/dense/hybrid/rerank return distinct trace stages and correct candidate IDs; known named POI and paraphrase retrieval; cross-destination filtering; missing model error/degradation. Test mocked adapters separately from actual semantic smoke. Save benchmark baseline early; do not tune against final held-out set. Existing catalog regression stays green.
