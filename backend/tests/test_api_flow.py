"""End-to-end API flow on a throw-away account (never mutates the seeded demo data)."""

from __future__ import annotations

import json
import uuid

import pytest_asyncio

from app.api.common import wait_for_background_runs
from tests.conftest import login, new_client

API = "/api/v1"


@pytest_asyncio.fixture
async def user():
    async with new_client() as c:
        pw = "FlowTestPass!2026"
        res = await c.post(
            f"{API}/auth/signup",
            json={
                "full_name": "Flow Tester",
                "email": f"flow-{uuid.uuid4().hex[:8]}@example.com",
                "password": pw,
                "confirm_password": pw,
            },
        )
        assert res.status_code == 201, res.text
        c.headers["X-CSRF-Token"] = res.json()["csrf_token"]
        yield c


async def _create_and_finish(c, prompt="Plan a 4-day Goa trip from Kolkata for 2 under 35000", **extra):
    res = await c.post(f"{API}/trips", json={"prompt": prompt, "start_date": "2027-01-12", "end_date": "2027-01-16", **extra})
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["run_id"] and body["run_public_id"].startswith("TG-")
    await wait_for_background_runs()
    return body


async def test_create_trip_runs_graph_and_persists_everything(user):
    body = await _create_and_finish(user)
    trip_id, run_ref = body["trip"]["id"], body["run_public_id"]

    run = (await user.get(f"{API}/runs/{run_ref}")).json()
    assert run["status"] == "completed" and run["ai_mode"] == "demo"
    assert run["input_tokens"] > 0 and run["total_cost_usd"] > 0

    trip = (await user.get(f"{API}/trips/{trip_id}")).json()
    assert trip["status"] == "completed" and trip["destination"].startswith("Goa")
    assert len(trip["days"]) >= 4 and trip["current_version"] == 1
    assert trip["estimated_cost_inr"] <= 35000 + 1

    events = (await user.get(f"{API}/runs/{run_ref}/events")).json()
    events = events["items"] if isinstance(events, dict) else events
    seqs = [e["seq"] for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    types = [e["type"] for e in events]
    assert types[0] == "run.created" and types[1] == "run.started" and types[-1] == "run.completed"
    started = {e["node_id"] for e in events if e["type"] == "agent.started"}
    assert {"supervisor", "destination", "transport", "accommodation", "itinerary", "aggregator"} <= started

    graph = (await user.get(f"{API}/runs/{run_ref}/graph")).json()
    assert graph["run_status"] == "completed"
    assert all(n["status"] == "completed" for n in graph["nodes"])

    cost = (await user.get(f"{API}/analytics/costs/runs/{run_ref}")).json()
    assert cost["reconciliation"]["reconciled"] is True


async def test_sse_stream_replays_and_terminates_with_end_event(user):
    body = await _create_and_finish(user)
    run_ref = body["run_public_id"]
    async with user.stream("GET", f"{API}/runs/{run_ref}/stream") as res:
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/event-stream")
        text = ""
        async for chunk in res.aiter_text():
            text += chunk
    assert "event: end" in text
    ids = [int(l.split(":", 1)[1]) for l in text.splitlines() if l.startswith("id:")]
    assert ids == sorted(ids) and ids[0] == 1
    first_payload = next(json.loads(l.split(":", 1)[1]) for l in text.splitlines() if l.startswith("data:") and l.strip() != "data: {}")
    assert first_payload["seq"] == 1

    cut = ids[len(ids) // 2]
    async with user.stream("GET", f"{API}/runs/{run_ref}/stream", headers={"Last-Event-ID": str(cut)}) as res:
        resumed = "".join([c async for c in res.aiter_text()])
    resumed_ids = [int(l.split(":", 1)[1]) for l in resumed.splitlines() if l.startswith("id:")]
    assert resumed_ids and min(resumed_ids) == cut + 1


async def test_evaluate_and_compare_two_runs(user):
    first = await _create_and_finish(user)
    second = await _create_and_finish(user, prompt="Plan a 4-day Goa trip from Kolkata for 2 under 40000", budget_inr=40000)
    ev = await user.post(f"{API}/evaluations", json={"run_id": first["run_public_id"]})
    assert ev.status_code == 201, ev.text
    assert ev.json()["kind"] == "deterministic" and ev.json()["overall_score"] is not None
    judge = await user.post(f"{API}/evaluations", json={"run_id": first["run_public_id"], "kind": "llm_judge"})
    assert judge.status_code in (400, 501)  # no fabricated judge scores in demo mode

    await user.post(f"{API}/evaluations", json={"run_id": second["run_public_id"]})
    cmp = await user.post(
        f"{API}/evaluations/compare", json={"run_ids": [first["run_public_id"], second["run_public_id"]]}
    )
    assert cmp.status_code == 200, cmp.text
    out = cmp.json()
    assert len(out["runs"]) == 2 and out["metric_names"]


async def test_seeded_comparison_tg1047_vs_tg1039():
    async with new_client() as c:
        c.headers["X-CSRF-Token"] = await login(c, "demo@travelgraph.local")
        res = await c.post(f"{API}/evaluations/compare", json={"run_ids": ["TG-1047", "TG-1039"]})
        assert res.status_code == 200, res.text
        out = res.json()
        by_id = {r["public_id"]: r for r in out["runs"]}
        assert by_id["TG-1047"]["wall_time_ms"] == 14200 and by_id["TG-1039"]["wall_time_ms"] == 31400
        assert by_id["TG-1047"]["total_cost_usd"] == 0.237
        assert any("demo" in n.lower() for n in out["notes"])  # fixtures are labeled, not passed off as live


async def test_benchmark_runs_real_graph_without_polluting_trips(user):
    cases = (await user.get(f"{API}/evaluations/benchmark/cases")).json()
    assert len(cases) >= 5
    res = await user.post(f"{API}/evaluations/benchmark", json={})
    assert res.status_code == 200, res.text
    out = res.json()
    assert out["total"] == len(cases) and out["passed"] == out["total"], out
    assert out["provenance"] == "demo"
    assert (await user.get(f"{API}/trips")).json()["total"] == 0


async def test_trip_crud_favorite_duplicate_versions_replan_and_filters(user):
    body = await _create_and_finish(user)
    tid = body["trip"]["id"]

    fav = await user.post(f"{API}/trips/{tid}/favorite")
    assert fav.status_code == 200 and fav.json()["is_favorite"] is True
    assert (await user.post(f"{API}/trips/{tid}/favorite", json={"is_favorite": False})).json()["is_favorite"] is False
    await user.post(f"{API}/trips/{tid}/favorite", json={"is_favorite": True})
    favs = (await user.get(f"{API}/trips", params={"status": "favorite"})).json()
    assert favs["total"] == 1

    patched = await user.patch(f"{API}/trips/{tid}", json={"title": "Renamed Goa", "notes": "bring sunscreen"})
    assert patched.status_code == 200 and patched.json()["title"] == "Renamed Goa"
    assert (await user.get(f"{API}/trips", params={"q": "renamed"})).json()["total"] == 1
    assert (await user.get(f"{API}/trips", params={"q": "zzzz-nothing"})).json()["total"] == 0

    dup = await user.post(f"{API}/trips/{tid}/duplicate")
    assert dup.status_code in (200, 201), dup.text
    assert dup.json()["id"] != tid and len(dup.json()["days"]) == len((await user.get(f"{API}/trips/{tid}")).json()["days"])
    assert (await user.get(f"{API}/trips")).json()["total"] == 2

    replan = await user.post(f"{API}/trips/{tid}/replan", json={"prompt": "Same trip but add a spa day"})
    assert replan.status_code == 202, replan.text
    assert replan.json()["revision_number"] == 2
    await wait_for_background_runs()
    versions = (await user.get(f"{API}/trips/{tid}/versions")).json()
    versions = versions["items"] if isinstance(versions, dict) else versions
    assert [v["version"] for v in versions][:2] in ([2, 1], [1, 2])
    restored = await user.post(f"{API}/trips/{tid}/versions/1/restore")
    assert restored.status_code == 200, restored.text

    assert (await user.delete(f"{API}/trips/{tid}")).status_code in (200, 204)
    assert (await user.get(f"{API}/trips/{tid}")).status_code == 404


async def test_needs_clarification_run_is_honest(user):
    res = await user.post(f"{API}/runs", json={"prompt": "Plan something nice for me please"})
    assert res.status_code == 202, res.text
    await wait_for_background_runs()
    ref = res.json().get("public_id") or res.json().get("run_public_id")
    run = (await user.get(f"{API}/runs/{ref}")).json()
    assert run["status"] == "needs_clarification"
    assert (await user.get(f"{API}/trips")).json()["total"] == 0
