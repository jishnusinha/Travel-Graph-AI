# Data sources

Terra reads a local snapshot. It does not scrape booking sites.

| Source | Used for | Status in this build |
|---|---|---|
| Wikivoyage MediaWiki API | Guide extracts, revision id, permalink | Adapter in `backend/app/ingestion/wikivoyage.py`. |
| English Wikipedia | Lead extract, revision id, Wikidata QID, page coordinates | Adapter in `backend/app/ingestion/wikipedia.py`. Disambiguation pages are not used as destination text. |
| OpenStreetMap Overpass | Named attraction, waterfall and monument nodes | Adapter in `backend/app/ingestion/osm.py`. A failed public interpreter is stored as an error. Coordinates are not guessed. |
| Wikimedia Commons | The Wikipedia article's page image, only with an allowed license | Adapter in `backend/app/ingestion/commons.py`. Files are saved under `data/knowledge/assets/`. |
| Editorial planning bands | Wide INR envelopes by destination kind | `data/knowledge/manifests/cost_ranges.json`. Method `editorial_planning_band`. Not a fare or room rate. |
| Project registry | Stable slugs and aliases | `data/knowledge/manifests/destinations.json` |
| Synthetic fixtures | Automated tests only | `backend/tests/fixtures/synthetic_corpus.json`, license `synthetic-test-only` |

The active snapshot `india-v1`, rebuilt from cache on 2026-11-24, has 42 Wikivoyage documents, 50 Wikipedia leads, 581 chunks, 48 Commons images, and 250 editorial cost rows. Lolegaon and Mawsynram have no Wikipedia page image. Nongriat, Dooars, and Mawlynnong have no page coordinates. The OpenStreetMap cache has no named POIs: four queries failed and the Manali query returned an empty list. Attraction rows do not contain invented OSM coordinates.

If a fetch fails, the CLI records the failure and does not invent article text.
