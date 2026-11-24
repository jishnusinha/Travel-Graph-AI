from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.base import utcnow
from app.graph.workflow import GRAPH_NODES, build_travel_graph
from app.models import (
    AgentRun,
    CostLineItem,
    ModelInvocation,
    ToolInvocation,
    Trip,
)
from app.observability.events import persist_event
from app.services.accounting import (
    DEMO_ROLE_COSTS,
    DEMO_ROLE_TOKENS,
    DEMO_WALL_TIME_MS,
    role_model_cost,
    role_tool_cost,
)
from app.services.trip_service import apply_plan_to_trip

settings = get_settings()

# Token / cost attribution for live demo runs (deterministic, labeled demo).
# Shared with seed + tests via app.services.accounting so numbers cannot drift.
LIVE_DEMO_ROLE_TOKENS = DEMO_ROLE_TOKENS
LIVE_DEMO_ROLE_COSTS = DEMO_ROLE_COSTS

# Which catalog tool each specialist owns (validator is deterministic Python, not billed)
NODE_TOOLS = {
    "destination": "travel_catalog.attractions",
    "transport": "travel_catalog.transport",
    "accommodation": "travel_catalog.hotels",
}

# Internal graph nodes that are not surfaced to the UI
HIDDEN_NODES = {"fanout"}

TERMINAL_EVENT_TYPES = {"run.completed", "run.failed", "run.needs_clarification"}


class SeqCounter:
    def __init__(self) -> None:
        self.n = 0

    def next(self) -> int:
        self.n += 1
        return self.n


async def _emit(db: AsyncSession, run_id: str, seq: SeqCounter, **kwargs: Any):
    return await persist_event(db, run_id=run_id, seq=seq.next(), **kwargs)


async def create_run(
    db: AsyncSession,
    *,
    user_id: str,
    payload: dict[str, Any],
    trip_id: str | None = None,
    public_id: str | None = None,
    revision_number: int = 1,
) -> AgentRun:
    run = AgentRun(
        public_id=public_id or f"TG-{uuid4().hex[:6].upper()}",
        user_id=user_id,
        trip_id=trip_id,
        thread_id=f"thread-{uuid4().hex}",
        status="pending",
        prompt=payload.get("prompt", ""),
        request_payload=payload,
        ai_mode=settings.ai_mode,
        model_name=settings.openai_model if settings.ai_mode == "openai" else "demo-local",
        cost_provenance="demo" if settings.ai_mode == "demo" else "estimated",
        revision_number=revision_number,
    )
    db.add(run)
    await db.flush()
    return run


async def execute_run(db: AsyncSession, run_id: str) -> AgentRun:
    run = (await db.execute(select(AgentRun).where(AgentRun.id == run_id))).scalar_one()
    seq = SeqCounter()
    run.status = "running"
    run.started_at = utcnow()
    await db.commit()

    await _emit(db, run.id, seq, type="run.created", status="pending", payload={"public_id": run.public_id})
    await _emit(db, run.id, seq, type="run.started", status="running", payload={})
    await db.commit()

    graph = build_travel_graph()
    initial = {
        "user_id": run.user_id,
        "trip_id": run.trip_id,
        "thread_id": run.thread_id,
        "run_id": run.id,
        "trip_request": run.request_payload,
        "messages": [],
        "agent_errors": [],
        "tool_results": {},
        "retry_count": 0,
        "revision_number": run.revision_number,
    }

    node_started: dict[str, datetime] = {}
    attempts: dict[str, int] = {}
    final_state: dict[str, Any] = dict(initial)
    demo = settings.ai_mode == "demo"
    acc = {"tin": 0, "tout": 0, "model": 0.0, "tool": 0.0}
    try:
        async for mode, event in graph.astream(initial, stream_mode=["tasks", "updates", "values"]):
            if mode == "values":
                final_state = event
                continue

            if mode == "tasks":
                node_id = event.get("name", "")
                if node_id.startswith("__") or node_id in HIDDEN_NODES:
                    continue
                if "input" in event and "result" not in event:  # task start
                    node_started[node_id] = utcnow()
                    attempts[node_id] = attempts.get(node_id, 0) + 1
                    state_in = event.get("input")
                    keys = list(state_in.keys())[:12] if isinstance(state_in, dict) else []
                    await _emit(
                        db,
                        run.id,
                        seq,
                        type="agent.started",
                        node_id=node_id,
                        status="running",
                        payload={"input_keys": keys, "attempt": attempts[node_id]},
                    )
                    await db.commit()
                continue

            # mode == "updates": a node finished
            for node_id, update in event.items():
                if node_id.startswith("__") or node_id in HIDDEN_NODES:
                    continue
                update = update or {}
                started = node_started.pop(node_id, None) or utcnow()

                if node_id in NODE_TOOLS:
                    tool_name = NODE_TOOLS[node_id]
                    fee = role_tool_cost(node_id) if demo else 0.0
                    await _emit(
                        db,
                        run.id,
                        seq,
                        type="tool.called",
                        node_id=node_id,
                        status="running",
                        payload={"tool": tool_name},
                    )
                    db.add(
                        ToolInvocation(
                            run_id=run.id,
                            node_id=node_id,
                            tool_name=tool_name,
                            status="succeeded",
                            duration_ms=120,
                            fee_usd=fee,
                            provenance="local-catalog",
                            output_summary={"ok": True},
                        )
                    )
                    await _emit(
                        db,
                        run.id,
                        seq,
                        type="tool.succeeded",
                        node_id=node_id,
                        status="succeeded",
                        payload={"tool": tool_name, "fee_usd": fee},
                    )
                    if demo and fee > 0:
                        acc["tool"] += fee
                        db.add(
                            CostLineItem(
                                run_id=run.id,
                                user_id=run.user_id,
                                category="tool",
                                agent_role=node_id,
                                tool_name=tool_name,
                                amount_usd=fee,
                                provenance="demo",
                            )
                        )

                if node_id == "validator":
                    for f in update.get("validation_findings") or []:
                        if f.get("severity") == "warning":
                            await _emit(
                                db,
                                run.id,
                                seq,
                                type="validation.warning",
                                node_id=node_id,
                                status="warning",
                                payload=f,
                            )

                await _emit(
                    db,
                    run.id,
                    seq,
                    type="state.updated",
                    node_id=node_id,
                    status="running",
                    payload={"keys": list(update.keys())},
                )

                usage: dict[str, Any] = {}
                if demo and node_id in LIVE_DEMO_ROLE_TOKENS:
                    tin, tout = LIVE_DEMO_ROLE_TOKENS[node_id]
                    model_cost = role_model_cost(node_id)
                    acc["tin"] += tin
                    acc["tout"] += tout
                    acc["model"] += model_cost
                    db.add(
                        ModelInvocation(
                            run_id=run.id,
                            node_id=node_id,
                            provider="demo",
                            model="demo-local",
                            input_tokens=tin,
                            output_tokens=tout,
                            estimated_cost_usd=model_cost,
                            cost_status="demo",
                            duration_ms=400,
                        )
                    )
                    db.add(
                        CostLineItem(
                            run_id=run.id,
                            user_id=run.user_id,
                            category="model",
                            agent_role=node_id,
                            model="demo-local",
                            amount_usd=model_cost,
                            tokens_in=tin,
                            tokens_out=tout,
                            provenance="demo",
                        )
                    )
                    usage = {
                        "model": "demo-local",
                        "tokens_in": tin,
                        "tokens_out": tout,
                        "cost_usd": round(model_cost + role_tool_cost(node_id), 6),
                    }

                duration_ms = int((utcnow() - started).total_seconds() * 1000)
                await _emit(
                    db,
                    run.id,
                    seq,
                    type="agent.completed",
                    node_id=node_id,
                    status="completed",
                    payload={
                        "duration_ms": max(duration_ms, 1),
                        "summary": _summarize(node_id, update),
                        "attempt": attempts.get(node_id, 1),
                        **usage,
                    },
                )
                await db.commit()
                await asyncio.sleep(0.02)

        run.final_plan = final_state.get("final_plan") or {}
        terminal_type = "run.completed"
        if final_state.get("needs_clarification"):
            run.status = "needs_clarification"
            run.error_message = final_state.get("clarification_prompt")
            terminal_type = "run.needs_clarification"
            await _finish_trip(db, run, status="draft")
        else:
            run.status = "completed"
            if (run.request_payload or {}).get("persist_trip") is not False:
                await _persist_trip_from_plan(db, run, final_state)

        if demo:
            run.input_tokens = acc["tin"]
            run.output_tokens = acc["tout"]
            run.model_cost_usd = round(acc["model"], 6)
            run.tool_cost_usd = round(acc["tool"], 6)
            run.total_cost_usd = round(acc["model"] + acc["tool"], 6)
            run.cost_provenance = "demo"

        run.completed_at = utcnow()
        if run.started_at:
            run.wall_time_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        if run.wall_time_ms <= 0 and demo:
            run.wall_time_ms = DEMO_WALL_TIME_MS
        payload: dict[str, Any] = {"wall_time_ms": run.wall_time_ms}
        if terminal_type == "run.needs_clarification":
            payload["clarification"] = run.error_message
        await _emit(db, run.id, seq, type=terminal_type, status=run.status, payload=payload)
        await db.commit()
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        # rollback expires loaded state; re-read before recording the failure
        run = (
            await db.execute(
                select(AgentRun).where(AgentRun.id == run_id).execution_options(populate_existing=True)
            )
        ).scalar_one()
        run.status = "failed"
        run.error_message = str(exc)[:2000]
        run.completed_at = utcnow()
        if run.started_at:
            run.wall_time_ms = int((run.completed_at - run.started_at).total_seconds() * 1000)
        for node_id in list(node_started):
            await _emit(
                db,
                run.id,
                seq,
                type="agent.failed",
                node_id=node_id,
                status="failed",
                payload={"error": str(exc)[:500]},
            )
        await _finish_trip(db, run, status="draft")
        await _emit(
            db,
            run.id,
            seq,
            type="run.failed",
            status="failed",
            payload={"error": str(exc)[:500]},
        )
        await db.commit()
    await db.refresh(run)
    return run


def _summarize(node_id: str, update: dict[str, Any] | None) -> str:
    update = update or {}
    if node_id == "supervisor":
        if update.get("needs_clarification"):
            return "Clarification needed"
        n = update.get("normalized_request") or {}
        return f"Parsed {n.get('destination')} · {n.get('days')} days"
    if node_id == "destination":
        r = update.get("research") or {}
        return f"Research: {len(r.get('attractions') or [])} attractions"
    if node_id == "transport":
        return f"{len(update.get('transport_options') or [])} transport options"
    if node_id == "accommodation":
        return f"{len(update.get('accommodation_options') or [])} stays compared"
    if node_id == "itinerary":
        return f"{len(update.get('itinerary_days') or [])} days scheduled"
    if node_id == "validator":
        return f"{len(update.get('validation_findings') or [])} findings"
    if node_id == "aggregator":
        return "Final plan compiled"
    return node_id


async def _finish_trip(db: AsyncSession, run: AgentRun, *, status: str) -> None:
    """Don't leave a trip stuck 'in_progress' when its run ended without a plan."""
    if not run.trip_id:
        return
    trip = await db.get(Trip, run.trip_id)
    if trip is not None and trip.status == "in_progress" and not trip.estimated_cost_inr:
        trip.status = status


async def _persist_trip_from_plan(db: AsyncSession, run: AgentRun, state: dict[str, Any]) -> None:
    plan = state.get("final_plan") or {}
    if not plan:
        return
    trip: Trip | None = None
    if run.trip_id:
        trip = await db.get(Trip, run.trip_id)
    if trip is None:
        trip = Trip(user_id=run.user_id, title="New Trip", slug="trip", destination="")
        db.add(trip)
        await db.flush()
        run.trip_id = trip.id
    summary = (
        "Generated by TravelGraph agents"
        if run.revision_number <= 1
        else f"Replanned by TravelGraph agents (revision {run.revision_number})"
    )
    await apply_plan_to_trip(
        db,
        trip,
        plan,
        prompt=run.prompt,
        change_summary=f"{summary} · {run.public_id}",
        status="completed",
    )


def graph_snapshot(status_by_node: dict[str, str] | None = None) -> dict[str, Any]:
    status_by_node = status_by_node or {}
    nodes = [
        {
            "id": n,
            "label": n.replace("_", " ").title(),
            "status": status_by_node.get(n, "pending"),
            "role": n,
        }
        for n in GRAPH_NODES
    ]
    # validator -> itinerary (bounded retry loop) is intentionally omitted from the
    # primary layout; the loop is visible through repeated itinerary invocations.
    edges = [
        {"id": "sup-dest", "source": "supervisor", "target": "destination"},
        {"id": "sup-trans", "source": "supervisor", "target": "transport"},
        {"id": "sup-acc", "source": "supervisor", "target": "accommodation"},
        {"id": "dest-itin", "source": "destination", "target": "itinerary"},
        {"id": "trans-itin", "source": "transport", "target": "itinerary"},
        {"id": "acc-itin", "source": "accommodation", "target": "itinerary"},
        {"id": "itin-val", "source": "itinerary", "target": "validator"},
        {"id": "val-agg", "source": "validator", "target": "aggregator"},
    ]
    return {"nodes": nodes, "edges": edges}
