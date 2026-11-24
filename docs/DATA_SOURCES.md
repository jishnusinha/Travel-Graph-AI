# Data sources

Terra reads a local snapshot. It does not scrape booking sites.

| Source | Used for | Status in this build |
|---|---|---|
| Wikivoyage MediaWiki API | Guide extracts, revision id, permalink | Adapter in `backend/app/ingestion/wikivoyage.py`. Run `scripts/ingest.ps1` when the network is available. |
| Wikipedia / Wikidata / OpenStreetMap / Commons | Optional enrichment | Not fetched by the default CLI yet. Missing fields stay null. |
| Project registry | Stable slugs and aliases | `data/knowledge/manifests/destinations.json` |
| Synthetic fixtures | Automated tests only | `backend/tests/fixtures/synthetic_corpus.json`, license `synthetic-test-only` |

If a fetch fails, the CLI records the failure and does not invent article text.
