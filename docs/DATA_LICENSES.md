# Data licenses

- Wikivoyage text is stored with `license_name: CC BY-SA 4.0` and a credit line when the adapter actually downloads a revision. Share-alike obligations stay with that text.
- OpenStreetMap data, if added later, is ODbL and must keep its own attribution. It is not mixed into Wikivoyage prose.
- Wikimedia Commons files are accepted only when a file license is recorded. This build does not ship photographs.
- Synthetic test fixtures are not sources. The UI labels `source_status=synthetic_test`.
- Catalog demo prices in `backend/app/providers/catalog.py` remain labeled sample estimates and are not used as RAG costs.
- Cost rows, when present, keep their method text. They are not live fares.

Do not commit API keys, SQLite WAL/SHM files, or downloaded model weights.
