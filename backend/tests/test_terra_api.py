from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.rag.store import import_corpus
from app.seed.demo_seed import DEMO_EMAIL, REVIEWER_EMAIL
from tests.embedder_double import TestEmbedder

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_corpus.json"


@pytest.fixture
def ready(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    embedder = TestEmbedder()
    import_corpus(payload, embedder=embedder, activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: embedder)


async def test_discovery_requires_auth(anon, ready):
    res = await anon.post("/api/v1/discovery/search", json={"query": "waterfalls"})
    assert res.status_code == 401


async def test_public_stats_expose_no_user_data(anon, ready):
    res = await anon.get("/api/v1/knowledge/stats")
    assert res.status_code == 200
    body = res.json()
    assert body["snapshot_id"] == "test-synthetic-v1"
    assert body["embedding_kind"] == "test_double"
    assert "email" not in res.text


async def test_discovery_cites_synthetic_source(demo, ready):
    res = await demo.post("/api/v1/discovery/search", json={"query": "quiet hills and waterfalls", "strategy": "keyword"})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["results"][0]["slug"] == "sohra"
    assert body["results"][0]["source_status"] == "synthetic_test"
    assert body["results"][0]["evidence"][0]["license"] == "synthetic-test-only"
    assert "budget_fit" in body["results"][0]["unknown_preferences"]


async def test_saved_places_are_private(demo, reviewer, ready):
    listed = await demo.get("/api/v1/destinations")
    dest_id = next(item["destination_id"] for item in listed.json()["items"] if item["slug"] == "sohra")
    saved = await demo.post("/api/v1/saved-destinations", json={"destination_id": dest_id})
    assert saved.status_code == 200, saved.text
    mine = await demo.get("/api/v1/saved-destinations")
    assert any(item["destination_id"] == dest_id for item in mine.json()["items"])
    theirs = await reviewer.get("/api/v1/saved-destinations")
    assert theirs.json()["items"] == []
    denied = await reviewer.delete(f"/api/v1/saved-destinations/{saved.json()['id']}")
    assert denied.status_code == 404


async def test_visual_search_is_explicitly_unavailable(demo, ready):
    res = await demo.post("/api/v1/discovery/visual", json={})
    assert res.status_code == 503
    assert "not" in res.json()["detail"].lower() or "unavailable" in res.json()["detail"].lower()


async def test_personalization_requires_consent(demo, ready):
    blocked = await demo.get("/api/v1/discovery/for-you")
    assert blocked.status_code == 403
    allowed = await demo.post("/api/v1/me/personalization", json={"consent": True, "interests": ["waterfalls"]})
    assert allowed.status_code == 200
    ranked = await demo.get("/api/v1/discovery/for-you")
    assert ranked.status_code == 200
    assert ranked.json()["generation_mode"] == "explicit_interest_match"


async def test_media_rejects_unknown_slug(anon, ready):
    missing = await anon.get("/api/v1/knowledge/media/not-a-real-place")
    assert missing.status_code == 404
    traversal = await anon.get("/api/v1/knowledge/media/../secrets")
    assert traversal.status_code == 404


async def test_knowledge_graph_and_entity_search(demo, ready):
    entities = await demo.get("/api/v1/knowledge/entities", params={"q": "Sohra"})
    assert entities.status_code == 200, entities.text
    assert any(item["label"] == "Sohra" for item in entities.json()["items"])
    graph = await demo.get("/api/v1/destinations/sohra/graph", params={"hops": 1})
    assert graph.status_code == 200, graph.text
    body = graph.json()
    assert body["seed"]["slug"] == "sohra"
    assert body["nodes"]
    assert any(edge["predicate"] in {"located_in", "within_80km_straight_line"} for edge in body["edges"])


async def test_compare_limits_and_missing_prices(demo, ready):
    listing = await demo.get("/api/v1/destinations")
    ids = [item["destination_id"] for item in listing.json()["items"][:2]]
    res = await demo.post("/api/v1/destinations/compare", json={"destination_ids": ids})
    assert res.status_code == 200, res.text
    too_many = await demo.post(
        "/api/v1/destinations/compare",
        json={"destination_ids": ["a", "b", "c", "d"]},
    )
    assert too_many.status_code == 422
    assert DEMO_EMAIL and REVIEWER_EMAIL
