# 06 — Agent integration and grounded travel planning

## Preserve the existing graph

Keep real StateGraph, parallel destination/transport/accommodation fanout, barrier before itinerary, bounded validator retry, aggregator, saved runs/events and SSE. Existing catalog path stays compatible (including legacy Goa fixture and metrics). In RAG mode avoid special-cased destination content and unused LLM calls. Check actual LangGraph version and graph construction before adding nodes. Update `GRAPH_NODES`, `GRAPH_EDGES`, frontend `lib/agents.ts`, layout and replay together; version graph metadata per run so historic replay renders old topology correctly.

## Discovery handoff

Preferred UX: search `/explore`, select canonical destination, prefill `/trips/new`. Direct planner request with no resolved destination calls discovery service/node, returns ranked candidates and `needs_clarification` terminal status using existing API semantics. Persist candidates + normalized constraints; ask user to choose, start new run linked to prior run (do not pretend checkpoint resume if not implemented). Unknown or ambiguous alias never falls back to Goa. No automatic choice of destination without user confirmation. Validate dates/travelers/budget; if absent, ask for missing planning fields rather than silently using demo dates outside catalog mode. Discovery queries may leave them unknown.

## Graph state extensions

Add typed fields: `knowledge_mode`, `snapshot_id`, `graph_version`, `destination_id`, `discovery_candidates`, `retrieval_run_ids`, `evidence_by_topic`, `allowed_attraction_ids`, `selected_transport_id`, `selected_stay_id`, `generation_mode`, `validation_findings`, `replan_requests`, `route_checks`, `budget_ranges`, `unknowns`. Use LangGraph reducers only for concurrent writes; keep specialist outputs separate to avoid update conflicts. Persist IDs, not large unbounded vectors or full user PII in checkpoint. Snapshot selected at run start, cannot change mid-run.

## Node contract

| Node | RAG mode responsibility |
|---|---|
| Supervisor | typed normalized request; explicit fields override parsed; resolve canonical ID; validate constraints; branch to discovery if ambiguous/missing |
| Discovery (conditional) | retrieve ranked destinations and evidence; pause for confirmation; no booking/price claims |
| Destination | retrieve destination-filtered attractions, culture, seasonality; canonical IDs/coordinates, evidence, unknowns; use actual service result |
| Transport | choose eligible curated options with origin/date/basis; use opt-in routing for road segments only; unsupported fare unknown |
| Accommodation | estimate ranges by room/nights/party and preferences; avoid naming fictional hotel as real inventory; actual options only if evidenced |
| Itinerary | use specialist results + evidence + constraint feedback; deterministic schedule offline, validated LLM selections live; only allowed POIs |
| Validator | deterministic date/day, activity, cost, route, citation, provenance, overlap and hard-constraint checks; bounded replan |
| Aggregator | persist validated plan, citation snapshot, evidence, remaining uncertainties, estimate label and validation status; no unsupported claims |

Upgrade `complete_json` provider to return typed data and usage metadata; actually consume validated output in live mode. Demo RAG mode should not call fake LLM to create irrelevant digest; compose using retrieved records. Catalog legacy can retain its existing fixture accounting. Use actual model API usage if present; distinguish not available from zero. No OpenAI key sent to frontend. Model choice configured; check supported SDK API before implementation.

## Planning algorithm (deterministic baseline)

Resolve destination, select verified attractions ranked by interests, remove duplicates, group by locality or coarse distance, assign days with arrival/departure buffers, duration and transit gaps. Avoid inventing opening hours or accessibility; use unknown flags. Include rest/meals as generic suggestions, not fictitious named attractions. Respect traveler count, pace and constraints. Costs computed from basis-aware ranges and actual selected activities; do not use arbitrary hardcoded ₹9,000 fallback as fact. For unknown cost show incomplete total, known subtotal and warnings. For live mode LLM selects IDs and day order; backend calculates times/ranges, resolves names and validates. If route provider absent use straight-line distance explicitly labeled and conservative feasibility warnings, not exact drive time.

## Validation and replanning

Return findings `code, severity, message, correctable, activity_id, evidence_ids`. Verify requested days, unique canonical POIs (intentional repeats allowed if marked), time windows, nonnegative durations, no overlap, transit feasibility, source support/ID membership, estimate basis, totals, currency and explicit constraints. Check route data freshness and geographic anomalies. If no route or current permit evidence, warn/unknown rather than claim verified. Budget low/high compare with budget: known minimum above = over; known maximum below and complete = within estimate; crossing = uncertain; missing = incomplete. Replan changes selected activities/pace/cost options in response to specific findings, not identical reruns. Limit retries (e.g. 2); if hard constraints unresolved, mark plan needs revision/partial, never successful validated plan. Do not overwrite previous usable version on failed generation. Save a new version only after authorized validation, preserve prior versions and evidence. Handle cancel/timeouts/failures with explicit terminal events.

## Real telemetry

Instrument actual service boundaries rather than creating fake tool invocations in `run_executor.py`. New trace events `retrieval.started`, `.query_normalized`, `.dense.completed`, `.sparse.completed`, `.fusion.completed`, `.rerank.completed`, `.graph.completed`, `.evidence_selected`, `.completed`, `.failed`; include IDs, stage timing, status, counts, snapshot and score metadata. Persist run/event order with sequence numbers and no cross-task session sharing. Reuse SSE event stream and auth. Keep legacy event parsing compatible; replay saved traces, no re-execution. Store actual model invocations including provider errors, input/output tokens when reported, estimated cost with price snapshot, local inference wall time and zero external API charges; machine running cost unknown. Do not replace actual timing with fixture values. See plan 10.

## Integration and acceptance

Update `trip_service.apply_plan_to_trip`, schemas and serialization to keep evidence on activities and versions, preserve old API shape. Tests: destination-free/ambiguous prompt, non-Goa destination, evidence affects itinerary, unknown cost, impossible budget, invalid dates, parallel barrier, bounded successful and unsuccessful replan, provider invalid JSON and timeout, stale snapshot, cross-user run isolation, prior catalog regression and replay. Run real offline end-to-end: discover → confirm → generate → inspect citations → save → reload → replay. Live provider tested with mock contract and optional actual user-configured key; no key required for release.
