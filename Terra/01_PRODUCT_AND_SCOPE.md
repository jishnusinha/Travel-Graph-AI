# 01 — Product definition and scope

## Identity

Terra is a source-grounded travel discovery and planning product. TravelGraph AI is its multi-agent intelligence engine and developer-facing studio. Keep repository name, existing account system, backend and frontend. Do not build a second app or migrate to Next.js. Use the brand lockup **terra. / Powered by TravelGraph AI** in the travel experience, and **TravelGraph AI / Intelligence Studio** in the technical workspace.

## User journeys

1. A visitor lands on `/`, sees real curated destination photography, enters a natural-language trip idea, and can preview public read-only discovery if the deployment enables it. Default local policy: discovery search is authenticated; preserve the pending query in sessionStorage across sign-in, then resume it. Never persist a sensitive query in URL parameters. Public landing can use a small static, attributed selection of snapshot destinations.
2. A user searches “quiet mountains, waterfalls and culture, five days from Kolkata, ₹25,000”. The system extracts constraints, identifies known/unknown attributes, retrieves evidence, groups hits by destination and shows ranked candidates. Budget suitability is unknown unless grounded in applicable cost estimates. A recommendation explains matched preferences with citations; it does not pretend to know live crowds or prices.
3. The user filters, switches to map, compares up to three destinations, opens a destination guide, asks a destination-specific question, saves a place, and chooses Plan trip. The canonical destination ID and preferences prefill the existing `/trips/new` form. They confirm dates, origin, travelers, total budget and transport preferences.
4. A LangGraph run researches the destination, transport and accommodation concurrently, generates an itinerary, validates route plausibility, evidence, dates and budget, and saves a version. A destination-free planning request returns discovery candidates/needs-clarification instead of choosing an arbitrary city. The user confirms one and starts a linked follow-up run.
5. The user sees an editable daily timeline, actual attraction pins, cited evidence, estimate ranges and unknowns. They can replace/reorder activities, regenerate a day, change constraints, view versions, restore, print/export and revisit saved trips. Every mutation is authorized and versioned.
6. A reviewer enters Intelligence Studio to inspect actual retrieval and agent traces, compare search strategies on the same snapshot, replay historical runs, explore a knowledge graph, examine measured evaluation and usage/cost provenance.

## Scope and priorities

| Priority | Deliverables |
|---|---|
| P0 | Baseline preservation, migration, licensed corpus snapshot, local hybrid search and rerank, citations, landing/discovery/details, grounded planner and validation, actual traces, retrieval lab and baseline evaluation |
| P1 | Map/list explorer, destination comparison, saved places, cost ranges and budget controls, partial replan and version history, optional routing/weather adapters, expanded evaluation |
| P2 | Provenanced entity graph, graph-enhanced retrieval and multi-hop tests, knowledge explorer, local visual similarity search, consent-based personalization and graph/visual benchmarks |

No bookings, payments, scraping proprietary reviews, live fares, OAuth expansion, subscriptions, social network or new database service as mandatory dependencies. Travel advice is informational; current permits, closures and safety conditions require verification and timestamped sources. All data labels must distinguish sourced facts, estimates, user input and unknowns.

## Initial data coverage

Target 50 canonical destinations, approximately 500 named attractions where evidence exists, 200 usable licensed images and 3,000 chunks if supported by actual corpus size. These are stretch inventory targets, not fabricated minimum counts. Start with 10–12 well-covered places, including the original Goa demo and other existing catalog places, and expand to 50. Do not count duplicates, fabricated content or boilerplate to reach targets. Report measured inventory and coverage gaps. See plan 03.

## Nonfunctional requirements

- Default runnable on Windows using PowerShell, local SQLite, no paid keys or cloud services. Internet is allowed for first installation/snapshot refresh, not required for offline runtime. Local mode must use real retrieval, not simulated relevance scores.
- Existing accounts, trips, replay, evaluations, cost views, version history, and catalog fixture behavior remain functional. Legacy mode remains selectable.
- Keep one coherent API contract, typed frontend client, accessible interactions, responsive layouts and robust failure/loading/empty states.
- Source citations must resolve to immutable evidence from the run's snapshot; never fabricate citation URLs, quote text, or telemetry.
- Do not claim a deterministic offline template is LLM-generated. Clearly label demo fixtures, actual local retrieval, optional live generation and unknown provider data.

## Product success scenarios

- Search by meaning with no destination named, open evidence, save a destination, create and reopen a cited trip without a key or internet after setup.
- A destination-specific query with no support returns a clear insufficient-evidence response.
- Existing Goa demo remains reproducible in legacy mode; a real RAG Goa run is distinguishable from it.
- A non-Goa destination uses actual retrieved attractions and a feasible schedule, not generic Goa copy.
- Reviewer can compare keyword/dense/hybrid/reranked/graph strategies, inspect ranked hits and open citations; numbers come from execution or explicitly tagged fixtures.
