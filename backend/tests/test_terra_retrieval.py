from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.config import get_settings
from app.rag.store import corpus_stats, import_corpus, search_sync
from app.services.discovery_service import discover
from tests.embedder_double import TestEmbedder

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_corpus.json"


def _user_id() -> str:
    from app.rag.store import connect
    from app.seed.demo_seed import DEMO_EMAIL

    conn = connect()
    try:
        row = conn.execute("SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)).fetchone()
    finally:
        conn.close()
    assert row is not None
    return row["id"]


@pytest.fixture
def synthetic_snapshot(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    embedder = TestEmbedder()
    imported = import_corpus(payload, embedder=embedder, activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: embedder)
    monkeypatch.setattr(get_settings(), "knowledge_mode", "rag")
    return imported


def test_import_counts_match_fixture(synthetic_snapshot):
    stats = corpus_stats()
    assert stats["status"] == "ready"
    assert stats["snapshot_id"] == "test-synthetic-v1"
    assert stats["documents"] == 3
    assert stats["chunks"] >= 3
    assert stats["embedding_kind"] == "test_double"
    assert synthetic_snapshot["chunks"] == stats["chunks"]


def test_keyword_finds_named_waterfall(synthetic_snapshot):
    found = search_sync(query="Nohkalikai Falls", user_id=_user_id(), strategy="keyword")
    assert found["strategy_applied"] == "keyword"
    blob = " ".join(item["text"] for item in found["evidence"])
    assert "Nohkalikai" in blob
    assert found["evidence"][0]["license_name"] == "synthetic-test-only"


def test_discovery_ranks_waterfalls_and_does_not_invent_atlantis(synthetic_snapshot):
    found = discover(query="quiet hills and waterfalls", user_id=_user_id(), strategy="keyword")
    slugs = [row["slug"] for row in found["results"]]
    assert slugs[0] == "sohra"
    assert "atlantis" not in slugs
    assert found["generation_mode"] == "deterministic_evidence"
    assert found["embedding_kind"] == "test_double"


def test_hybrid_records_dense_stage(synthetic_snapshot):
    found = search_sync(query="waterfalls in the hills", user_id=_user_id(), strategy="hybrid")
    assert found["dense_count"] > 0
    assert found["keyword_count"] > 0
    assert found["strategy_applied"] == "hybrid"
    assert "test_double" == found["embedding_kind"]


def test_rerank_fallback_is_not_labeled_reranked(monkeypatch, synthetic_snapshot):
    monkeypatch.setattr("app.rag.store.rerank_scores", lambda query, texts: None)
    found = search_sync(query="waterfalls", user_id=_user_id(), strategy="hybrid_rerank")
    assert found["reranked"] is False
    assert "rerank_unavailable" in found["warnings"]
    assert found["strategy_applied"] != "hybrid_rerank"


def test_hybrid_rerank_is_applied_when_the_cross_encoder_scores(monkeypatch, synthetic_snapshot):
    monkeypatch.setattr(
        "app.rag.store.rerank_scores",
        lambda query, texts: [float(len(texts) - index) for index in range(len(texts))],
    )
    found = search_sync(query="waterfalls in the hills", user_id=_user_id(), strategy="hybrid_rerank")
    assert found["dense_count"] > 0
    assert found["keyword_count"] > 0
    assert found["reranked"] is True
    assert found["strategy_applied"] == "hybrid_rerank"
    assert "fell_back_to_keyword" not in found["warnings"]


def test_missing_model_keyword_fallback(monkeypatch, synthetic_snapshot):
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: None)
    found = search_sync(query="waterfalls", user_id=_user_id(), strategy="hybrid")
    assert "dense_unavailable" in found["warnings"] or "fell_back_to_keyword" in found["warnings"]
    assert found["strategy_applied"] == "keyword"


def test_graph_links_nearby_fixture_places(synthetic_snapshot):
    from app.rag.store import connect

    conn = connect()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM knowledge_relationships WHERE predicate = 'within_80km_straight_line'"
        ).fetchone()
    finally:
        conn.close()
    assert row["n"] >= 1


def test_unanswerable_question_abstains(synthetic_snapshot):
    from app.services.discovery_service import answer_about

    answer = answer_about("sohra", "penguin colony Antarctica", _user_id())
    assert answer["insufficient_evidence"] is True
