from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.config import get_settings
from app.db.session import SessionLocal
from app.models import User
from app.rag.store import import_corpus
from app.seed.demo_seed import DEMO_EMAIL
from app.services.run_executor import create_run, execute_run
from tests.embedder_double import TestEmbedder

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_corpus.json"


async def test_rag_plan_uses_snapshot_not_goa_catalog(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    embedder = TestEmbedder()
    import_corpus(payload, embedder=embedder, activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: embedder)
    monkeypatch.setattr(get_settings(), "knowledge_mode", "rag")
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
        run = await create_run(
            db,
            user_id=user.id,
            payload={
                "prompt": "Plan a 4-day Sohra trip from Kolkata for two under ₹25000 with waterfalls.",
                "destination": "Sohra",
                "budget_inr": 25000,
                "travelers": 2,
                "persist_trip": False,
            },
        )
        await db.commit()
        run = await execute_run(db, run.id)
    assert run.status == "completed", run.error_message
    assert run.knowledge_mode == "rag"
    assert run.cost_provenance == "local_retrieval_no_llm"
    assert run.total_cost_usd == 0
    plan = run.final_plan
    assert plan["generation_mode"] == "deterministic_evidence"
    assert plan["title"] != "Goa Escape Plan"
    titles = [a["title"] for day in plan["days"] for a in day["activities"]]
    assert "Nohkalikai Falls" in titles
    assert "Calangute Beach" not in titles
    assert plan["budget_breakdown"]["verification_status"] == "unknown"
    assert plan["budget_breakdown"]["total"] is None
    evidence = {item["citation_id"]: item.get("text") or "" for item in plan["research"]["evidence"]}
    for day in plan["days"]:
        assert day["activities"], "itinerary day is empty"
        for activity in day["activities"]:
            for citation_id in activity["citation_ids"]:
                assert activity["title"].lower() in evidence[citation_id].lower()
            if activity["category"] not in {"transport", "note"}:
                assert activity["citation_ids"]


async def test_rag_without_destination_does_not_pick_goa(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    import_corpus(payload, embedder=TestEmbedder(), activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: TestEmbedder())
    monkeypatch.setattr(get_settings(), "knowledge_mode", "rag")
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
        run = await create_run(
            db,
            user_id=user.id,
            payload={"prompt": "quiet hills and waterfalls for five days under ₹25000", "budget_inr": 25000, "persist_trip": False},
        )
        await db.commit()
        run = await execute_run(db, run.id)
    assert run.status == "needs_clarification"
    assert run.final_plan == {} or run.final_plan is None or not run.final_plan.get("days")


def test_unrelated_evidence_is_not_attached_to_another_sight():
    from app.services.planner_knowledge import rag_itinerary

    state = {
        "normalized_request": {"destination": "Sohra", "days": 2, "budget_inr": 10000, "travelers": 2},
        "research": {
            "attractions": [
                {"name": "Nohkalikai Falls", "category": "waterfall", "citation_id": "c1"},
                {"name": "Secret Viewpoint", "category": "viewpoint", "citation_id": "c1"},
                {"name": "Nohkalikai Falls", "category": "waterfall", "citation_id": "c1"},
            ],
            "evidence": [{"citation_id": "c1", "text": "Nohkalikai Falls drops from the plateau."}],
        },
        "transport_options": [],
        "accommodation_options": [],
    }
    built = rag_itinerary(state)
    titles = [activity["title"] for day in built["itinerary_days"] for activity in day["activities"]]
    assert titles.count("Nohkalikai Falls") == 1
    assert "Secret Viewpoint" not in titles
    cited = [activity for day in built["itinerary_days"] for activity in day["activities"] if activity["citation_ids"]]
    assert cited
    assert all(activity["citation_ids"] == ["c1"] and activity["title"] == "Nohkalikai Falls" for activity in cited)
    assert all(day["activities"] for day in built["itinerary_days"])


async def test_invalid_dates_ask_for_a_correction(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    import_corpus(payload, embedder=TestEmbedder(), activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: TestEmbedder())
    monkeypatch.setattr(get_settings(), "knowledge_mode", "rag")
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
        run = await create_run(
            db,
            user_id=user.id,
            payload={
                "prompt": "Plan Sohra",
                "destination": "Sohra",
                "start_date": "2026-05-10",
                "end_date": "2026-05-01",
                "budget_inr": 25000,
                "persist_trip": False,
            },
        )
        await db.commit()
        run = await execute_run(db, run.id)
    assert run.status == "needs_clarification"
    assert "Invalid dates" in (run.error_message or "")


async def test_impossible_budget_is_flagged_when_stored_estimates_exceed_it(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    estimates = [
        {"category": category, "low_inr": 1000, "high_inr": high, "basis": "curated_range", "method": "manual_review", "confidence": "low"}
        for category, high in (
            ("transport", 20000),
            ("accommodation", 20000),
            ("meals", 4000),
            ("local_travel", 2000),
            ("attractions", 1000),
            ("contingency", 1000),
        )
    ]
    for dest in payload["destinations"]:
        if dest["slug"] == "sohra":
            dest["estimates"] = estimates
    import_corpus(payload, embedder=TestEmbedder(), activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: TestEmbedder())
    monkeypatch.setattr(get_settings(), "knowledge_mode", "rag")
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
        run = await create_run(
            db,
            user_id=user.id,
            payload={
                "prompt": "Plan a 3-day Sohra trip with waterfalls.",
                "destination": "Sohra",
                "budget_inr": 1000,
                "travelers": 2,
                "persist_trip": False,
            },
        )
        await db.commit()
        run = await execute_run(db, run.id)
    assert run.status == "completed", run.error_message
    budget = run.final_plan["budget_breakdown"]
    assert budget["total"] is not None and budget["total"] > 1000
    codes = {item["code"] for item in run.final_plan["validation_findings"]}
    assert "budget_exceeded" in codes


async def test_rejected_model_output_keeps_the_deterministic_plan(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    import_corpus(payload, embedder=TestEmbedder(), activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: TestEmbedder())
    settings = get_settings()
    monkeypatch.setattr(settings, "knowledge_mode", "rag")
    monkeypatch.setattr(settings, "ai_mode", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_model", "gpt-test")

    class Rejecting:
        async def complete_json(self, **kwargs):
            user = json.loads(kwargs["user"])
            evidence_id = user["evidence"][0]["evidence_id"]
            return {"claims": [{"text": "A helicopter transfer costs exactly 99999 rupees.", "evidence_ids": [evidence_id]}]}

    monkeypatch.setattr("app.providers.llm.get_llm_provider", lambda: Rejecting())
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
        run = await create_run(
            db,
            user_id=user.id,
            payload={
                "prompt": "Plan a 4-day Sohra trip from Kolkata for two under ₹25000 with waterfalls.",
                "destination": "Sohra",
                "budget_inr": 25000,
                "travelers": 2,
                "persist_trip": False,
            },
        )
        await db.commit()
        run = await execute_run(db, run.id)
    assert run.status == "completed", run.error_message
    plan = run.final_plan
    assert plan["generation_mode"] == "deterministic_evidence"
    assert "openai_output_rejected" in plan["generation_warnings"]
    assert "99999" not in plan["narrative"]
    assert run.cost_provenance == "local_retrieval_no_llm"
    titles = [activity["title"] for day in plan["days"] for activity in day["activities"]]
    assert "Nohkalikai Falls" in titles


async def test_openai_narrative_uses_only_supported_claims(monkeypatch):
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    import_corpus(payload, embedder=TestEmbedder(), activate=True)
    monkeypatch.setattr("app.rag.store.get_embedder", lambda: TestEmbedder())
    settings = get_settings()
    monkeypatch.setattr(settings, "knowledge_mode", "rag")
    monkeypatch.setattr(settings, "ai_mode", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_model", "gpt-test")

    class Retrying:
        def __init__(self):
            self.calls = 0

        async def complete_json(self, **kwargs):
            self.calls += 1
            user = json.loads(kwargs["user"])
            evidence_id = user["evidence"][0]["evidence_id"]
            if self.calls == 1:
                return {"claims": [{"text": "A helicopter transfer costs exactly 99999 rupees.", "evidence_ids": ["missing-id"]}]}
            return {
                "claims": [
                    {
                        "text": "Sohra is a hill settlement known for waterfalls including Nohkalikai Falls.",
                        "evidence_ids": [evidence_id],
                    }
                ],
                "unknowns": ["Live ticket prices are not in the excerpts."],
                "insufficient_evidence": False,
            }

    provider = Retrying()
    monkeypatch.setattr("app.providers.llm.get_llm_provider", lambda: provider)
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
        run = await create_run(
            db,
            user_id=user.id,
            payload={
                "prompt": "Plan a 4-day Sohra trip from Kolkata for two under ₹25000 with waterfalls.",
                "destination": "Sohra",
                "budget_inr": 25000,
                "travelers": 2,
                "persist_trip": False,
            },
        )
        await db.commit()
        run = await execute_run(db, run.id)
    assert run.status == "completed", run.error_message
    assert provider.calls == 2
    plan = run.final_plan
    assert plan["generation_mode"] == "openai_grounded"
    assert "Nohkalikai" in plan["narrative"]
    assert "99999" not in plan["narrative"]
    assert run.cost_provenance == "openai_unmetered"
    titles = [activity["title"] for day in plan["days"] for activity in day["activities"]]
    assert "Nohkalikai Falls" in titles
    assert "Atlantis" not in titles


async def test_validator_flags_empty_days_duplicates_and_missing_evidence(monkeypatch):
    from app.graph.nodes import validator_node

    monkeypatch.setattr(get_settings(), "knowledge_mode", "rag")

    state = {
        "normalized_request": {"days": 1, "budget_inr": 1000},
        "itinerary_days": [
            {
                "day_number": 1,
                "activities": [
                    {"title": "Nohkalikai Falls", "category": "waterfall", "citation_ids": ["c1"]},
                    {"title": "Nohkalikai Falls", "category": "waterfall", "citation_ids": []},
                ],
            },
            {"day_number": 2, "activities": []},
        ],
        "budget_breakdown": {
            "intercity_travel": 100,
            "accommodation": 100,
            "meals": 100,
            "local_travel": 100,
            "attractions": 100,
            "contingency": 100,
            "total": 600,
            "verification_status": "estimate",
        },
        "transport_options": [{"name": "stored"}],
        "accommodation_options": [{"name": "stored"}],
        "retry_count": 0,
    }
    result = await validator_node(state)
    codes = {item["code"] for item in result["validation_findings"]}
    assert "empty_day" in codes
    assert "duplicate_attraction" in codes
    assert "uncited_activity" in codes


def test_replan_day_keeps_the_other_days():
    from app.services.run_executor import _scope_replan_day

    class TripVersion:
        current_version = 4

    merged = _scope_replan_day(
        {"days": [{"day_number": 1, "title": "regenerated"}, {"day_number": 2, "title": "discarded"}]},
        {
            "replan_day": 1,
            "expected_version": 4,
            "prior_days": [{"day_number": 1, "title": "old"}, {"day_number": 2, "title": "keep"}],
        },
        TripVersion(),
    )
    assert merged is not None
    assert merged["days"][0]["title"] == "regenerated"
    assert merged["days"][1]["title"] == "keep"
