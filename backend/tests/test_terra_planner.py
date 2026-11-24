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
