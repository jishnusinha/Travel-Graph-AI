from __future__ import annotations

import time
from typing import Any

import pytest

from app.config import Settings
from app.graph.nodes import (
    GOA_BUDGET,
    _parse_destination,
    _request_dates,
    route_after_supervisor,
    route_after_validator,
    validator_node,
)
from app.graph.state import TravelGraphState, merge_dicts
from app.graph.workflow import GRAPH_EDGES, GRAPH_NODES, build_travel_graph
from app.providers import llm as llm_module
from app.providers.llm import DemoLLMProvider, demo_latency_override, get_llm_provider


def _initial(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "trip_request": request,
        "messages": [],
        "agent_errors": [],
        "tool_results": {},
        "retry_count": 0,
        "revision_number": 1,
    }


async def _collect(request: dict[str, Any], modes=("updates", "tasks")):
    """Run the graph and return (ordered chunks, final state)."""
    graph = build_travel_graph()
    chunks: list[tuple[str, Any, float]] = []
    final: dict[str, Any] = {}
    async for mode, data in graph.astream(_initial(request), stream_mode=[*modes, "values"]):
        if mode == "values":
            final = data
        else:
            chunks.append((mode, data, time.perf_counter()))
    return chunks, final


def _update_nodes(chunks) -> list[str]:
    return [n for mode, data, _ in chunks if mode == "updates" for n in data]


GOA = {"prompt": "Plan a 5-day Goa trip for two under ₹35,000 with beaches and local food.", "budget_inr": 35000, "travelers": 2}


# --------------------------------------------------------------------------- structure
def test_compiled_graph_has_real_fanout_and_join_edges():
    drawable = build_travel_graph().get_graph()
    node_ids = set(drawable.nodes)
    assert set(GRAPH_NODES) <= node_ids
    edges = {(e.source, e.target) for e in drawable.edges}
    for specialist in ("destination", "transport", "accommodation"):
        assert ("fanout", specialist) in edges  # parallel fan-out
        assert (specialist, "itinerary") in edges  # fan-in
    assert ("itinerary", "validator") in edges
    assert ("validator", "aggregator") in edges and ("validator", "itinerary") in edges  # bounded loop
    assert ("supervisor", "fanout") in edges and ("supervisor", "__end__") in edges
    assert {("supervisor", "destination"), ("validator", "aggregator")} <= set(GRAPH_EDGES)


# --------------------------------------------------------------------------- happy path
async def test_goa_happy_path_runs_every_agent_in_order_and_budget_math_holds():
    chunks, final = await _collect(GOA)
    order = _update_nodes(chunks)
    assert order[0] == "supervisor"
    assert order[1] == "fanout"
    assert set(order[2:5]) == {"destination", "transport", "accommodation"}
    assert order[5:] == ["itinerary", "validator", "aggregator"]  # join: itinerary runs exactly once

    plan = final["final_plan"]
    assert plan["title"] == "Goa Escape Plan"
    assert len(plan["days"]) == 5
    bb = plan["budget_breakdown"]
    assert {k: bb[k] for k in GOA_BUDGET} == GOA_BUDGET
    assert bb["total"] == 34850 == plan["estimated_cost_inr"]
    assert bb["remaining"] == 150
    assert sum(GOA_BUDGET.values()) == 34850
    assert not [f for f in plan["validation_findings"] if f["severity"] == "error"]
    assert plan["transport"]["total_inr"] == 12500
    assert plan["accommodation"]["total_inr"] == 9200


async def test_parallel_specialists_all_start_before_any_finishes():
    chunks, _ = await _collect(GOA, modes=("tasks",))
    names = ("destination", "transport", "accommodation")
    start_idx = {}
    result_idx = {}
    for i, (_, data, _) in enumerate(chunks):
        if data["name"] in names:
            (result_idx if "result" in data else start_idx)[data["name"]] = i
    assert set(start_idx) == set(names) == set(result_idx)
    assert max(start_idx.values()) < min(result_idx.values())


async def test_parallel_branch_wall_time_is_max_not_sum_of_delays():
    token = demo_latency_override.set(0.12)  # per-node delays: dest 0.156s, transport 0.12s, stay 0.138s
    try:
        chunks, _ = await _collect(GOA, modes=("tasks",))
    finally:
        demo_latency_override.reset(token)
    times: dict[str, dict[str, float]] = {}
    for _, data, ts in chunks:
        times.setdefault(data["name"], {})["result" if "result" in data else "start"] = ts
    branch = max(times[n]["result"] for n in ("destination", "transport", "accommodation")) - min(
        times[n]["start"] for n in ("destination", "transport", "accommodation")
    )
    sequential_floor = 0.156 + 0.12 + 0.138
    assert branch < sequential_floor * 0.85, f"branch took {branch:.3f}s, looks sequential"


async def test_state_reducers_merge_parallel_writes():
    _, final = await _collect(GOA, modes=())
    assert {"destination_catalog", "transport_catalog", "hotel_catalog"} <= set(final["tool_results"])
    roles = [m["role"] for m in final["messages"]]
    assert roles[0] == "supervisor" and roles[-1] == "aggregator"
    assert set(roles) >= {"destination", "transport", "accommodation", "itinerary", "validator"}
    assert merge_dicts({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}
    assert merge_dicts(None, {"b": 2}) == {"b": 2}  # type: ignore[arg-type]


async def test_other_destinations_use_catalog_and_pass_validation():
    chunks, final = await _collect(
        {"prompt": "4-day Udaipur heritage trip for 2 under ₹40,000.", "budget_inr": 40000, "travelers": 2}
    )
    plan = final["final_plan"]
    assert plan["destination"] == "Udaipur"
    assert len(plan["days"]) == 4
    assert all(d["activities"] for d in plan["days"])
    assert plan["estimated_cost_inr"] == plan["budget_breakdown"]["total"] <= 40000
    assert _update_nodes(chunks).count("itinerary") == 1


# --------------------------------------------------------------------------- branching
async def test_missing_destination_stops_after_supervisor_with_clarification():
    chunks, final = await _collect({"prompt": "Plan a relaxing 5-day trip for two under ₹35,000.", "travelers": 2})
    assert _update_nodes(chunks) == ["supervisor"]
    assert final["needs_clarification"] is True
    assert "destination" in final["clarification_prompt"].lower()
    assert not final.get("final_plan")


async def test_end_before_start_is_rejected_not_silently_fixed():
    chunks, final = await _collect({"prompt": "Plan Goa from 2027-01-16 to 2027-01-12 for 2.", "travelers": 2})
    assert _update_nodes(chunks) == ["supervisor"]
    assert final["needs_clarification"] is True
    assert "date" in final["clarification_prompt"].lower()


async def test_structured_dates_define_day_count():
    _, final = await _collect(
        {"prompt": "Plan Jaipur", "destination": "Jaipur", "start_date": "2027-03-05", "end_date": "2027-03-07",
         "budget_inr": 30000, "travelers": 2}
    )
    assert len(final["final_plan"]["days"]) == 3
    assert final["final_plan"]["start_date"] == "2027-03-05"


# --------------------------------------------------------------------------- bounded loop
async def test_budget_conflict_loops_back_to_itinerary_then_terminates():
    chunks, final = await _collect(
        {"prompt": "Plan a 5-day Goa luxury trip for 2 under ₹8,000.", "budget_inr": 8000, "travelers": 2}
    )
    order = _update_nodes(chunks)
    assert order.count("itinerary") == 3  # first pass + 2 retries (cap), then gives up gracefully
    assert order.count("validator") == 3
    assert order[-1] == "aggregator" and order.count("aggregator") == 1
    plan = final["final_plan"]
    assert any(f["code"] == "budget_exceeded" for f in plan["validation_findings"])
    assert "exceed" in plan["recommendation"].lower()
    assert final["retry_count"] == 3


def test_route_after_validator_respects_retry_cap():
    err = {"severity": "error", "correctable": True, "code": "budget_exceeded"}
    base: TravelGraphState = {"validation_findings": [err]}  # type: ignore[typeddict-item]
    assert route_after_validator({**base, "retry_count": 1}) == "itinerary"
    assert route_after_validator({**base, "retry_count": 2}) == "itinerary"
    assert route_after_validator({**base, "retry_count": 3}) == "aggregator"
    warning = {"severity": "warning", "correctable": False, "code": "missing_transport"}
    assert route_after_validator({"validation_findings": [warning], "retry_count": 0}) == "aggregator"  # type: ignore[typeddict-item]
    assert route_after_validator({"validation_findings": [], "retry_count": 0}) == "aggregator"  # type: ignore[typeddict-item]


def test_route_after_supervisor():
    assert route_after_supervisor({"needs_clarification": True}) == "end_clarify"  # type: ignore[typeddict-item]
    assert route_after_supervisor({"needs_clarification": False}) == "fanout"  # type: ignore[typeddict-item]
    assert route_after_supervisor({}) == "fanout"  # type: ignore[typeddict-item]


# --------------------------------------------------------------------------- deterministic validator
async def test_validator_is_deterministic_python_and_flags_problems():
    state: dict[str, Any] = {
        "normalized_request": {"days": 5, "budget_inr": 35000},
        "itinerary_days": [{"day_number": 1, "activities": [{"title": "x"}]}, {"day_number": 2, "activities": []}],
        "budget_breakdown": {
            "intercity_travel": 1, "accommodation": 1, "meals": 1, "local_travel": 1, "attractions": 1,
            "contingency": 1, "total": 99999,
        },
        "transport_options": [],
        "accommodation_options": [],
        "retry_count": 0,
    }
    out = await validator_node(state)  # type: ignore[arg-type]
    codes = {f["code"] for f in out["validation_findings"]}
    assert {"day_count_mismatch", "empty_day", "budget_exceeded", "budget_math", "missing_transport", "missing_stay"} <= codes
    assert out["retry_count"] == 1


async def test_validator_passes_clean_plan():
    out = await validator_node(
        {
            "normalized_request": {"days": 1, "budget_inr": 10000},
            "itinerary_days": [{"day_number": 1, "activities": [{"title": "x"}]}],
            "budget_breakdown": {
                "intercity_travel": 1, "accommodation": 1, "meals": 1, "local_travel": 1, "attractions": 1,
                "contingency": 1, "total": 6,
            },
            "transport_options": [{"mode": "x"}],
            "accommodation_options": [{"name": "y"}],
            "retry_count": 0,
        }  # type: ignore[arg-type]
    )
    assert out["validation_findings"] == []
    assert out["retry_count"] == 0


# --------------------------------------------------------------------------- parsing + providers
def test_destination_parsing_never_guesses():
    assert _parse_destination("Plan a 5-day Goa trip", None) == "Goa"
    assert _parse_destination("weekend in Darjeeling please", None) == "Darjeeling"
    assert _parse_destination("Trip to Lisbon", None) == "Lisbon"
    assert _parse_destination("Plan a relaxing 5-day trip for two under ₹35,000.", None) is None
    assert _parse_destination("anything", "Manali") == "Manali"


def test_request_dates_prefers_structured_then_prompt():
    assert _request_dates({"start_date": "2027-01-01", "end_date": "2027-01-03"}, "x 2030-01-01 2030-01-02") == (
        "2027-01-01", "2027-01-03")
    assert _request_dates({}, "from 2027-01-12 to 2027-01-16") == ("2027-01-12", "2027-01-16")
    assert _request_dates({}, "no dates") == (None, None)


def test_openai_mode_without_key_fails_with_actionable_error(monkeypatch):
    settings = Settings(_env_file=None, ai_mode="openai", openai_api_key="", openai_model="")
    monkeypatch.setattr(llm_module, "get_settings", lambda: settings)
    with pytest.raises(RuntimeError) as exc:
        get_llm_provider()
    assert "OPENAI_API_KEY" in str(exc.value) and "AI_MODE=demo" in str(exc.value)
    assert "sk-" not in str(exc.value)


def test_demo_mode_is_default_even_if_a_key_is_present(monkeypatch):
    settings = Settings(_env_file=None, ai_mode="demo", openai_api_key="sk-test", openai_model="m")
    monkeypatch.setattr(llm_module, "get_settings", lambda: settings)
    assert isinstance(get_llm_provider(), DemoLLMProvider)


async def test_demo_llm_is_deterministic_and_offline():
    llm = DemoLLMProvider()
    a = await llm.complete_json(system="s", user="u", schema_hint="h", node_id="supervisor")
    b = await llm.complete_json(system="s", user="u", schema_hint="h", node_id="supervisor")
    assert a == b and a["provider"] == "demo"
