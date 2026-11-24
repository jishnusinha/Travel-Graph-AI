from __future__ import annotations

import json

from app.ingestion.commons import license_allowed, select_image
from app.ingestion.names import dedupe_named, name_key
from app.ingestion.osm import parse_elements
from app.ingestion.wikipedia import normalize_page
from app.rag.store import connect, import_corpus


def test_name_key_folds_plural_falls():
    assert name_key("Seven Sisters Falls") == name_key("Seven Sister Falls")
    assert name_key("Ward's Lake") == name_key("Wards Lake")
    assert name_key("The Vithala Temple") == name_key("Vithala Temple")


def test_dedupe_keeps_coordinates_and_both_names():
    rows = dedupe_named(
        [
            {"name": "Seven Sister Falls", "category": "mentioned_in_text", "coordinate_status": "unknown"},
            {
                "name": "Seven Sisters Falls",
                "lat": 25.1,
                "lon": 91.7,
                "coordinate_status": "osm_node",
                "osm_type": "node",
                "osm_id": 10,
                "source_refs": [{"source": "openstreetmap", "osm_id": 10}],
            },
        ]
    )
    assert len(rows) == 1
    assert rows[0]["lat"] == 25.1
    assert "Seven Sisters Falls" in rows[0]["aliases"] or rows[0]["name"] == "Seven Sisters Falls"


def test_wikipedia_missing_redirect_and_coordinates():
    missing = normalize_page("Nowhere", {"query": {"pages": [{"title": "Nowhere", "missing": True}]}})
    assert missing["status"] == "missing"
    redirected = normalize_page(
        "Dzükou Valley",
        {
            "query": {
                "redirects": [{"from": "Dzükou Valley", "to": "Dzüko Valley"}],
                "pages": [
                    {
                        "title": "Dzüko Valley",
                        "pageid": 99,
                        "extract": "Dzüko Valley is a valley on the border of Nagaland and Manipur.",
                        "fullurl": "https://en.wikipedia.org/wiki/Dz%C3%BCko_Valley",
                        "revisions": [{"revid": 123, "timestamp": "2026-01-01T00:00:00Z"}],
                        "coordinates": [{"lat": 25.5, "lon": 94.1}],
                        "pageprops": {"wikibase_item": "Q123"},
                    }
                ],
            }
        },
    )
    assert redirected["status"] == "ok"
    assert redirected["redirected"] is True
    assert redirected["revision_id"] == "123"
    assert redirected["wikidata_qid"] == "Q123"
    assert redirected["coordinate_status"] == "wikipedia_page"
    assert redirected["license_name"] == "CC BY-SA 4.0"
    assert "index.php" in redirected["permalink"] and "oldid=123" in redirected["permalink"]


def test_wikipedia_disambiguation_and_malformed_payload():
    page = normalize_page("Goa", {"query": {"pages": [{"title": "Goa (disambiguation)", "pageprops": {"disambiguation": ""}}]}})
    assert page["status"] == "disambiguation"
    assert page["content"] == ""
    assert normalize_page("Goa", {"query": {}})["status"] == "malformed"


def test_osm_drops_unnamed_and_far_points():
    payload = {
        "elements": [
            {"type": "node", "id": 1, "lat": 25.27, "lon": 91.73, "tags": {"tourism": "attraction"}},
            {"type": "node", "id": 2, "lat": 25.271, "lon": 91.731, "tags": {"name": "Nohkalikai Falls", "waterway": "waterfall"}},
            {"type": "way", "id": 3, "center": {"lat": 10.0, "lon": 77.0}, "tags": {"name": "Far Peak", "natural": "peak"}},
        ]
    }
    rows = parse_elements(payload, center=(25.27, 91.73), radius_m=6000)
    assert [row["name"] for row in rows] == ["Nohkalikai Falls"]
    assert rows[0]["osm_id"] == 2
    assert rows[0]["license_name"] if False else rows[0]["source_refs"][0]["license_name"] == "ODbL 1.0"


def test_commons_license_filter():
    assert license_allowed("CC BY-SA 4.0")
    assert license_allowed("CC0")
    assert license_allowed("Public domain") is True
    assert license_allowed("CC BY-NC-SA 4.0") is False
    assert license_allowed("CC BY-ND 4.0") is False
    assert license_allowed("") is False
    payload = {
        "query": {
            "pages": [
                {"title": "File:Restricted.jpg", "imageinfo": [{"thumburl": "https://upload.wikimedia.org/a.jpg", "extmetadata": {"LicenseShortName": {"value": "CC BY-NC 4.0"}}}]},
                {
                    "title": "File:Open.jpg",
                    "imageinfo": [
                        {
                            "thumburl": "https://upload.wikimedia.org/open.jpg",
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Open.jpg",
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0"},
                                "Artist": {"value": "<a href=\"/wiki/User:A\">Ada</a>"},
                            },
                        }
                    ],
                },
            ]
        }
    }
    chosen = select_image(payload)
    assert chosen is not None
    assert chosen["license_name"] == "CC BY-SA 4.0"
    assert chosen["author"] == "Ada"
    assert "Ada" in chosen["attribution"]


def test_repeated_attraction_names_share_one_row():
    payload = {
        "snapshot_id": "alias-dedupe-v1",
        "destinations": [
            {
                "slug": "alias-sohra",
                "name": "Alias Sohra",
                "kind": "village",
                "documents": [
                    {
                        "source_type": "synthetic_test",
                        "title": "Alias",
                        "revision_id": "a1",
                        "content": "Seven Sisters Falls is mentioned once.",
                        "license_name": "synthetic-test-only",
                    }
                ],
                "attractions": [
                    {"name": "Seven Sister Falls", "category": "mentioned_in_text"},
                    {
                        "name": "Seven Sisters Falls",
                        "category": "waterfall",
                        "lat": 25.1,
                        "lon": 91.7,
                        "coordinate_status": "osm_node",
                        "osm_type": "node",
                        "osm_id": 55,
                    },
                ],
            }
        ],
    }
    import_corpus(payload, embedder=None, activate=False)
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT a.name, a.lat, a.aliases, a.coordinate_status
            FROM attractions a
            JOIN destinations d ON d.id = a.destination_id
            WHERE d.slug = 'alias-sohra'
            """
        ).fetchall()
    finally:
        conn.close()
    assert len(rows) == 1
    assert rows[0]["lat"] == 25.1
    aliases = json.loads(rows[0]["aliases"] or "[]")
    assert "Seven Sisters Falls" in aliases or rows[0]["name"] == "Seven Sisters Falls"


def test_wikipedia_request_records_timeout(monkeypatch):
    import httpx

    from app.ingestion import wikipedia

    def explode(*args, **kwargs):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr("app.ingestion.http.time.sleep", lambda *_: None)
    monkeypatch.setattr("app.ingestion.http.httpx.get", explode)
    record = wikipedia.fetch_page("Timeout Place", refresh=True)
    assert record["status"] == "error"
    assert record["error"] == "timeout"
