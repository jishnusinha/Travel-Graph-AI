# Data licenses

- Wikivoyage text is stored with `license_name: CC BY-SA 4.0` and a credit line when the adapter actually downloads a revision. Share-alike obligations stay with that text.
- Wikipedia lead text uses the same CC BY-SA 4.0 credit and a revision permalink. It is stored as its own document, not pasted into the Wikivoyage extract.
- OpenStreetMap names and coordinates are ODbL 1.0. They stay on attraction `source_refs` and are not copied into guide prose. A failed Overpass query stores an error and leaves coordinates unknown.
- Wikimedia Commons files are stored only when the file license is CC0, public domain, CC BY, or CC BY-SA. NC and ND files are rejected. Attribution, author, license URL and the file page are stored with the image.
- Synthetic test fixtures are not sources. The UI labels `source_status=synthetic_test`.
- Catalog demo prices in `backend/app/providers/catalog.py` remain labeled sample estimates and are not used as RAG costs.
- Cost rows, when present, keep their method text. They are not live fares.

Do not commit API keys, SQLite WAL/SHM files, or downloaded model weights.
