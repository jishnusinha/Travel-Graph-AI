from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.rag.fusion import rrf_fuse
from app.rag.graphwalk import bfs_evidence
from app.rag.intent import parse_intent
from app.rag.textutil import chunk_sections, fts_match_query
from app.rag.compose import compose_answer, validate_llm_claims
from tests.embedder_double import TestEmbedder

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_corpus.json"


def test_rrf_arithmetic_and_tie_break():
    fused = rrf_fuse([["b", "a"], ["a", "c"]])
    scores = dict(fused)
    assert scores["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert scores["b"] == pytest.approx(1 / 61)
    assert fused[0][0] == "a"
    tied = rrf_fuse([["b"], ["a"]])
    assert [cid for cid, _ in tied] == ["a", "b"]


def test_intent_extracts_budget_days_and_origin():
    intent = parse_intent("quiet waterfalls, five days from Kolkata, ₹25,000 for 2 travelers")
    assert intent["budget_inr"] == 25000
    assert intent["duration_days"] == 5
    assert intent["origin"] == "Kolkata"
    assert intent["travelers"] == 2
    assert "waterfalls" in intent["interests"]


def test_fts_query_strips_operators():
    assert fts_match_query('waterfalls AND "goa" OR (beach*)') == '"waterfalls" OR "and" OR "goa" OR "or" OR "beach"'


def test_chunker_keeps_heading():
    chunks = chunk_sections("== See ==\n" + ("waterfalls " * 40) + "\n== Eat ==\nMomos and tea are common here in the market.")
    assert chunks[0]["section_path"] == "See"
    assert any(c["section_path"] == "Eat" for c in chunks)


def test_compose_abstains_without_overlap():
    result = compose_answer("penguin colony", [{"text": "Sohra is known for waterfalls including Nohkalikai Falls in the hills.", "citation_id": "c1"}])
    assert result["insufficient_evidence"] is True
    assert result["generation_mode"] == "deterministic_evidence"


def test_llm_claim_must_cite_selected_evidence():
    evidence = {"c1": {"text": "Nohkalikai Falls drops beside the Sohra plateau."}}
    kept, rejected = validate_llm_claims(
        [
            {"text": "Nohkalikai Falls is beside the plateau.", "evidence_ids": ["c1"]},
            {"text": "Visit Atlantis tomorrow.", "evidence_ids": ["c1"]},
            {"text": "A cited claim.", "evidence_ids": ["missing"]},
        ],
        evidence,
    )
    assert len(kept) == 1
    assert "claim_not_supported_by_excerpt" in rejected
    assert "citation_not_in_selected_evidence" in rejected


def test_graph_walk_is_bounded():
    edges = [
        {"subject_id": "a", "object_id": "b", "evidence_chunk_id": "c1", "predicate": "located_in", "method": "registry"},
        {"subject_id": "b", "object_id": "c", "evidence_chunk_id": "c2", "predicate": "located_in", "method": "registry"},
        {"subject_id": "c", "object_id": "d", "evidence_chunk_id": "c3", "predicate": "located_in", "method": "registry"},
    ]
    walked = bfs_evidence(seed_entity_ids=["a"], edges=edges, max_hops=2)
    assert [e["evidence_chunk_id"] for e in walked] == ["c1", "c2"]


def test_cosine_prefers_aligned_vector():
    from app.rag.fusion import cosine_scores

    matrix = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    scores = cosine_scores(matrix, np.array([1.0, 0.0], dtype=np.float32))
    assert float(scores[0]) > float(scores[1])


def test_embedder_double_is_labeled():
    vectors = TestEmbedder().encode(["waterfalls in the hills"], is_query=True)
    assert vectors.shape == (1, 32)
    assert TestEmbedder.kind == "test_double"


def test_wikivoyage_listing_names_do_not_invent_coordinates():
    from app.ingestion.wikivoyage import listing_names

    names = listing_names("1 Panaji — the capital\nnot a listing\nAgonda — a beach\n2 Nohkalikai Falls – a plunge")
    assert names == ["Panaji", "Agonda", "Nohkalikai Falls"]


def test_lead_excerpt_uses_the_opening_paragraph():
    from app.ingestion.wikivoyage import lead_excerpt

    text = "Goa is a state on the west coast. It has beaches.\n\nUnderstand\nLater text."
    assert lead_excerpt(text) == "Goa is a state on the west coast. It has beaches."


def test_fixture_is_labeled_synthetic():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for dest in payload["destinations"]:
        assert dest["source_status"] == "synthetic_test"
        for doc in dest["documents"]:
            assert doc["license_name"] == "synthetic-test-only"
