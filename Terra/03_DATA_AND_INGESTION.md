# 03 — Travel data, licensing and reproducible ingestion

## Data sources and adapters

| Source | Endpoint / documentation | Use |
|---|---|---|
| Wikivoyage | https://en.wikivoyage.org/w/api.php ; https://dumps.wikimedia.org/enwikivoyage/ | Travel guide sections, transport, attractions and culture |
| Wikipedia | https://en.wikipedia.org/w/api.php | Supplemental history, geography, named entities |
| Wikidata | https://www.wikidata.org/wiki/Wikidata:Data_access | Canonical IDs, aliases and coordinates when available |
| OpenStreetMap | https://overpass-turbo.eu/ ; https://download.geofabrik.de/asia/india.html | Named POIs, coordinates, categories, OSM IDs |
| Wikimedia Commons | https://commons.wikimedia.org/w/api.php | Licensed photography, credit metadata and file-page links |
| Open-Meteo | https://open-meteo.com/en/docs/historical-weather-api | Historical monthly weather aggregates / optional current forecasts |
| OSRM | https://project-osrm.org/ | Optional online or self-hosted routing; never assume public endpoint SLA |
| Curated estimates | Project-authored CSV/JSON with recorded method and source | Indicative cost ranges; not live quotes |

Check current API terms and licenses before ingestion. Use a descriptive User-Agent with a configurable real project contact, timeouts, exponential backoff/jitter, Retry-After, caching, low concurrency, rate limits and resumability. Avoid live mass querying Overpass; cache modest region queries or use extracts for bulk. For official tourism content, only ingest text/assets with documented reuse permission or compatible license; otherwise link to the official source without copying. Do not scrape TripAdvisor, Booking, Google Maps, travel blogs, or restricted sites. No fake source content or LLM-generated corpus substituted for actual documents.

## Canonical destination registry

Create `data/knowledge/manifests/destinations.json` with stable UUID or deterministic namespaced ID, slug, name, aliases, region, country, coordinates if verified, Wikivoyage/Wikipedia page titles, Wikidata QID when known, OSM boundary/feature IDs if available, source status. Seed candidate registry below, validate each page and identity before accepting. Distinguish regions and cities; avoid conflating Darjeeling district/city or Kerala state/backwaters. `kind=region|city|village|area`.

| Region | Candidate destinations (50 total targets; adjust after verification) |
|---|---|
| Meghalaya (8) | Shillong, Sohra/Cherrapunji, Mawlynnong, Dawki, Jowai, Nongriat, Mawsynram, Tura |
| Sikkim (8) | Gangtok, Pelling, Ravangla, Namchi, Yuksom, Lachung, Lachen, Zuluk |
| North Bengal (7) | Darjeeling, Kalimpong, Kurseong, Mirik, Lava, Lolegaon, Dooars |
| Arunachal Pradesh (7) | Tawang, Ziro, Bomdila, Dirang, Itanagar, Pasighat, Mechuka |
| Assam (5) | Guwahati, Kaziranga, Majuli, Sivasagar, Tezpur |
| Nagaland (4) | Kohima, Dimapur, Dzüko Valley, Mokokchung |
| Other (11) | Goa, Manali, Jaipur, Udaipur, Munnar, Kerala Backwaters, Rishikesh, Varanasi, Hampi, Mysuru, Puducherry |

Begin with Goa, Manali, Jaipur, Udaipur, Munnar, Rishikesh, Darjeeling, Shillong, Sohra, Gangtok, Pelling, Ziro. Retain any other existing catalog destinations/aliases discovered during audit. Coverage depends on usable data, not arbitrary counts.

## Document ingestion

1. Fetch `action=query` page IDs, redirects and revision metadata; use `action=parse` HTML sections or revision-specific content. `prop=extracts&explaintext=1` may be useful for initial coverage but preserve headings and listings from parsed HTML where available. Record page ID, revision ID, canonical URL, revision permalink, timestamps, content hash, language, license, credit URL and adapter version. Handle missing/disambiguation/redirect pages explicitly. Keep source hierarchy and original attribution.
2. Extract readable section text and meaningful POI listing fields, remove nav/edit chrome, duplicate templates, ads, scripts and raw HTML. Keep sanitized original text; treat all source text as untrusted data, never prompt instructions.
3. Normalize Unicode, whitespace, aliases, regions and canonical IDs. Deduplicate exact hashes and near-duplicates conservatively; retain separate attribution when sources differ. Record missing information as null, not inferred facts.
4. Section-aware chunking: initial 250–450 tokens, 40–70 token overlap, avoid splitting listing records. Store section path, offsets relative to normalized revision text, token count, content hash, language, destination IDs, entity IDs, topic, verified geo if relevant. Use stable hash-derived chunk IDs based on source revision + section + offsets/hash. Parent document retained for evidence viewer. Keep adjacent chunks available for context without doubling citations.
5. OSM: query named POIs via bounded `nwr` requests or regional extract for `tourism=attraction|viewpoint|museum`, `waterway=waterfall`, `natural=peak`, `historic=*` etc.; use center coordinates for ways/relations and label them as approximate. Validate lat/lon and OSM type/id. Do not turn unnamed features into named attractions. OSM and Wikidata identifiers can link to text; proximity is not identity. Store geometry provenance and source date; avoid treating missing opening hours as open.
6. Images: query Commons file metadata, MIME type, dimensions, file page, author, attribution, license name/URL, allowed usage and thumbnail URLs. Accept only explicitly compatible public domain/CC licenses for the intended use; reject unknown/restricted files. Manually review hero images for destination correctness, quality and credit. Download and optimize to local WebP/JPEG with dimensions, credits and modifications recorded. Do not use full mockup images as pages, generated photographs as factual location photos, or hotlinks as offline assets. Provide meaningful alt text and safe placeholder if unavailable.
7. Weather: aggregate dated historical observations into monthly normals with years, units, coverage and uncertainty; separate from forecasts. Cost estimates include INR range, origin (transport), season, per person/per room/per party basis, source/method, checked date and confidence. No arbitrary current prices or unsupported crowd-level claims.

## License and attribution

Record source-specific license at revision/file level. Wikimedia text commonly requires attribution and share-alike; Commons licenses vary by file; OSM data under ODbL has attribution and database reuse conditions. Preserve original source notices, credit URLs, modifications, and share-alike obligations where applicable. Store source datasets and derived OSM datasets with clear provenance and licensing boundaries. Add `docs/DATA_SOURCES.md`, `docs/DATA_LICENSES.md`, machine-readable credits manifest, and UI attribution/source drawer. Do not assume a publicly readable source is freely reusable. Verify source terms when running ingestion.

## Snapshot and indexing lifecycle

`manifest.json`: snapshot ID, created_at UTC, schema version, corpus version, adapter versions, source counts, document revision list/hashes, chunking config, embedding model ID/revision/dimension, rerank model revision, index checksums, image credits, graph version, coverage report. Keep immutable snapshots; stage new builds in temp dir, validate all referential links and checksum, then activate atomically. Failed refresh must leave previous snapshot usable. Existing trip/version citations remain resolvable (persist exact evidence snippets and revision refs or retain old snapshot). Idempotent repeat ingestion of identical revisions produces same IDs and no duplicates. Resume failed adapters; record errors per place and source. No silent deletion of user trips on refresh.

## CLI and PowerShell

Implement module entrypoints (actual syntax may adapt to existing scripts):

```powershell
.\scripts\ingest.ps1 -Snapshot india-v1 -Limit 12
.\scripts\build-index.ps1 -Snapshot india-v1
.\scripts\ingest.ps1 -Snapshot india-v2 -Resume
.\scripts\evaluate-rag.ps1 -Snapshot india-v1
```

CLI subcommands `fetch`, `normalize`, `chunk`, `embed`, `build`, `verify`, `activate`, `stats`, `refresh`. `--dry-run`, `--limit`, `--resume`, `--offline`, `--snapshot`, explicit activation. Offline fixture for unit tests must be small real/licensed excerpts or explicitly synthetic test text, not mislabeled corpus. Setup builds/installs a usable snapshot with model cache; if external source unavailable, use verified bundled/release snapshot or state blocker clearly. Do not invent a snapshot download URL. Include storage size and model download estimates measured during setup.

## Acceptance

- At least 12 verified destination records or report precisely why blocked; grow to target based on available content. All public records have attribution and provenance. No orphan chunks or invalid coordinates.
- Rerun ingestion on cached snapshot offline with deterministic IDs. Simulated interrupted build leaves active snapshot intact. Source adapter tests cover redirect, missing page, timeout, rate limit, malformed payload and duplicate records.
- Gallery credits and source drawer resolve to stored data; snapshot manifest counts equal actual DB/index counts. After setup disconnect network and run sample retrieval and destination pages with no remote requests.
