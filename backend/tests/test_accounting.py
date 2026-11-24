from __future__ import annotations

import pytest
from sqlalchemy import select

from app.api.common import wait_for_background_runs
from app.db.session import SessionLocal
from app.models import AgentEvent, AgentRun, CostLineItem, ModelInvocation, ToolInvocation, User
from app.seed.demo_seed import DEMO_EMAIL
from app.services.accounting import (
    DEMO_INPUT_TOKENS,
    DEMO_MODEL_COST,
    DEMO_OUTPUT_TOKENS,
    DEMO_ROLE_COSTS,
    DEMO_ROLE_TOKENS,
    DEMO_ROLE_TOOL_COSTS,
    DEMO_TOOL_COST,
    DEMO_TOTAL_COST,
    demo_totals_for_nodes,
    line_item_totals,
    reconciles,
    role_model_cost,
    validate_demo_math,
)
from app.services.run_executor import create_run, execute_run

# The numbers from the product spec, written out independently of the module under test
SPEC_ROLE_TOKENS = {
    "supervisor": (2900, 740),
    "destination": (5600, 1250),
    "transport": (4300, 1100),
    "accommodation": (4600, 1250),
    "itinerary": (7600, 2400),
    "aggregator": (3960, 720),
}
SPEC_ROLE_COSTS = {
    "supervisor": 0.018,
    "destination": 0.043,
    "transport": 0.038,
    "accommodation": 0.041,
    "itinerary": 0.074,
    "aggregator": 0.023,
}
GOA_PROMPT = "Plan a 5-day Goa trip for two under ₹35,000 with beaches and local food."


# --------------------------------------------------------------------------- pure math
def test_role_tokens_match_spec_and_sum_to_36420():
    assert DEMO_ROLE_TOKENS == SPEC_ROLE_TOKENS
    assert sum(i for i, _ in DEMO_ROLE_TOKENS.values()) == DEMO_INPUT_TOKENS == 28960
    assert sum(o for _, o in DEMO_ROLE_TOKENS.values()) == DEMO_OUTPUT_TOKENS == 7460
    assert DEMO_INPUT_TOKENS + DEMO_OUTPUT_TOKENS == 36420


def test_role_costs_sum_to_total_and_split_into_model_plus_tool():
    assert DEMO_ROLE_COSTS == SPEC_ROLE_COSTS
    assert sum(DEMO_ROLE_COSTS.values()) == pytest.approx(0.237, abs=1e-9)
    assert DEMO_MODEL_COST + DEMO_TOOL_COST == pytest.approx(DEMO_TOTAL_COST, abs=1e-9)
    assert sum(DEMO_ROLE_TOOL_COSTS.values()) == pytest.approx(0.020, abs=1e-9)
    model_sum = sum(role_model_cost(r) for r in DEMO_ROLE_COSTS)
    assert model_sum == pytest.approx(0.217, abs=1e-9)
    for role, total in DEMO_ROLE_COSTS.items():
        assert role_model_cost(role) + DEMO_ROLE_TOOL_COSTS.get(role, 0.0) == pytest.approx(total, abs=1e-9)


def test_validate_demo_math_passes():
    validate_demo_math()


def test_partial_totals_count_only_executed_roles():
    only_supervisor = demo_totals_for_nodes(["supervisor", "supervisor"])  # duplicates counted once
    assert only_supervisor["input_tokens"] == 2900
    assert only_supervisor["output_tokens"] == 740
    assert only_supervisor["total_cost_usd"] == pytest.approx(0.018)
    everything = demo_totals_for_nodes(list(DEMO_ROLE_TOKENS))
    assert everything["total_cost_usd"] == pytest.approx(0.237, abs=1e-9)
    assert everything["input_tokens"] == 28960


def test_reconciles_tolerance():
    assert reconciles(0.237, 0.237000000001)
    assert not reconciles(0.237, 0.238)


# --------------------------------------------------------------------------- seeded TG-1047
async def _run(db, public_id: str) -> AgentRun:
    return (await db.execute(select(AgentRun).where(AgentRun.public_id == public_id))).scalar_one()


async def test_seeded_tg1047_headline_numbers():
    async with SessionLocal() as db:
        run = await _run(db, "TG-1047")
        assert run.wall_time_ms == 14200
        assert (run.input_tokens, run.output_tokens) == (28960, 7460)
        assert run.model_cost_usd == pytest.approx(0.217, abs=1e-9)
        assert run.tool_cost_usd == pytest.approx(0.020, abs=1e-9)
        assert run.total_cost_usd == pytest.approx(0.237, abs=1e-9)
        assert run.cost_provenance == "demo"


async def test_seeded_tg1047_line_items_reconcile_per_role_and_overall():
    async with SessionLocal() as db:
        run = await _run(db, "TG-1047")
        items = (await db.execute(select(CostLineItem).where(CostLineItem.run_id == run.id))).scalars().all()
        by_role: dict[str, float] = {}
        for it in items:
            by_role[it.agent_role] = by_role.get(it.agent_role, 0.0) + it.amount_usd
        for role, expected in SPEC_ROLE_COSTS.items():
            assert by_role[role] == pytest.approx(expected, abs=1e-9), role
        totals = await line_item_totals(db, run.id)
        assert totals["amount_usd"] == pytest.approx(0.237, abs=1e-9)
        assert (totals["tokens_in"], totals["tokens_out"]) == (28960, 7460)
        assert sum(i.amount_usd for i in items if i.category == "tool") == pytest.approx(0.020, abs=1e-9)
        assert sum(i.amount_usd for i in items if i.category == "model") == pytest.approx(0.217, abs=1e-9)

        models = (await db.execute(select(ModelInvocation).where(ModelInvocation.run_id == run.id))).scalars().all()
        assert {m.node_id: (m.input_tokens, m.output_tokens) for m in models} == SPEC_ROLE_TOKENS
        tools = (await db.execute(select(ToolInvocation).where(ToolInvocation.run_id == run.id))).scalars().all()
        assert sum(t.fee_usd for t in tools) == pytest.approx(0.020, abs=1e-9)


async def test_seeded_wall_time_is_not_the_sum_of_overlapping_agent_durations():
    async with SessionLocal() as db:
        run = await _run(db, "TG-1047")
        events = (
            await db.execute(select(AgentEvent).where(AgentEvent.run_id == run.id).order_by(AgentEvent.seq))
        ).scalars().all()
        durations = [e.payload["duration_ms"] for e in events if e.type == "agent.completed"]
        assert sum(durations) > run.wall_time_ms  # overlap => naive sum exceeds wall time
        starts = {e.node_id: e.ts for e in events if e.type == "agent.started"}
        ends = {e.node_id: e.ts for e in events if e.type == "agent.completed"}
        parallel = ["destination", "transport", "accommodation"]
        assert max(starts[n] for n in parallel) < min(ends[n] for n in parallel)


async def test_cost_endpoint_reports_reconciliation_for_tg1047(demo):
    res = await demo.get("/api/v1/analytics/costs/runs/TG-1047")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["reconciliation"]["reconciled"] is True
    assert body["reconciliation"]["tokens_reconciled"] is True
    assert body["reconciliation"]["line_items_total_usd"] == pytest.approx(0.237, abs=1e-9)
    agents = {a["agent"]: a for a in body["by_agent"]}
    for role, expected in SPEC_ROLE_COSTS.items():
        assert agents[role]["cost_usd"] == pytest.approx(expected, abs=1e-9)
    assert sum(a["share_pct"] for a in body["by_agent"]) == pytest.approx(100.0, abs=0.5)
    assert body["wall_time_ms"] == 14200
    # waterfall shows overlapping spans
    spans = {w["node"]: w for w in body["waterfall"]}
    assert spans["transport"]["start_ms"] < spans["destination"]["end_ms"]


async def test_all_seeded_runs_reconcile_line_items_to_run_totals():
    async with SessionLocal() as db:
        runs = (await db.execute(select(AgentRun))).scalars().all()
        assert len(runs) >= 25
        for run in runs:
            totals = await line_item_totals(db, run.id)
            assert reconciles(run.total_cost_usd, totals["amount_usd"]), run.public_id
            assert (totals["tokens_in"], totals["tokens_out"]) == (run.input_tokens, run.output_tokens), run.public_id
            assert run.model_cost_usd + run.tool_cost_usd == pytest.approx(run.total_cost_usd, abs=1e-6), run.public_id


# --------------------------------------------------------------------------- live demo run
async def _execute(payload: dict) -> tuple[AgentRun, list[AgentEvent]]:
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == DEMO_EMAIL))).scalar_one()
        run = await create_run(db, user_id=user.id, payload={**payload, "persist_trip": False})
        await db.commit()
        run = await execute_run(db, run.id)
        events = (
            await db.execute(select(AgentEvent).where(AgentEvent.run_id == run.id).order_by(AgentEvent.seq))
        ).scalars().all()
        return run, list(events)


async def test_live_demo_run_totals_match_canonical_accounting():
    run, events = await _execute({"prompt": GOA_PROMPT, "budget_inr": 35000, "travelers": 2})
    await wait_for_background_runs()
    assert run.status == "completed"
    assert (run.input_tokens, run.output_tokens) == (28960, 7460)
    assert run.total_cost_usd == pytest.approx(0.237, abs=1e-9)
    assert run.model_cost_usd == pytest.approx(0.217, abs=1e-9)
    assert run.tool_cost_usd == pytest.approx(0.020, abs=1e-9)
    async with SessionLocal() as db:
        totals = await line_item_totals(db, run.id)
    assert reconciles(run.total_cost_usd, totals["amount_usd"])
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert events[-1].type == "run.completed"


async def test_retried_itinerary_is_billed_per_invocation_and_still_reconciles():
    # Impossible budget forces the bounded validator -> itinerary retry loop
    run, events = await _execute(
        {"prompt": "Plan a 5-day Goa luxury trip for 2 under ₹8,000.", "budget_inr": 8000, "travelers": 2}
    )
    itinerary_starts = [e for e in events if e.type == "agent.started" and e.node_id == "itinerary"]
    assert len(itinerary_starts) == 3  # first pass + 2 bounded retries
    assert [e.payload["attempt"] for e in itinerary_starts] == [1, 2, 3]
    expected_in = 28960 + 2 * DEMO_ROLE_TOKENS["itinerary"][0]
    assert run.input_tokens == expected_in
    async with SessionLocal() as db:
        totals = await line_item_totals(db, run.id)
        invocations = (
            await db.execute(
                select(ModelInvocation).where(ModelInvocation.run_id == run.id, ModelInvocation.node_id == "itinerary")
            )
        ).scalars().all()
    assert len(invocations) == 3
    assert reconciles(run.total_cost_usd, totals["amount_usd"])
    assert run.total_cost_usd == pytest.approx(0.237 + 2 * role_model_cost("itinerary"), abs=1e-6)


async def test_clarification_run_only_bills_the_supervisor():
    run, events = await _execute({"prompt": "Plan a relaxing 5-day trip for two under ₹35,000.", "travelers": 2})
    assert run.status == "needs_clarification"
    assert (run.input_tokens, run.output_tokens) == DEMO_ROLE_TOKENS["supervisor"]
    assert run.total_cost_usd == pytest.approx(0.018)
    assert events[-1].type == "run.needs_clarification"
    assert not any(e.node_id == "itinerary" for e in events)
