"""Read-side projections of a run's persisted events (graph state, waterfall, node detail).

Everything here is derived from stored rows only, so live runs and historical replays
render identically and never trigger a model call.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.graph.workflow import GRAPH_NODES
from app.models import AgentEvent, AgentRun
from app.schemas.runs import GraphEdgeOut, GraphNodeOut, GraphOut
from app.services.run_executor import graph_snapshot

TERMINAL_RUN_STATUSES = {"completed", "failed", "needs_clarification"}


def _ms_between(a: datetime | None, b: datetime | None) -> int | None:
    if a is None or b is None:
        return None
    return int((b - a).total_seconds() * 1000)


def build_graph(run: AgentRun, events: list[AgentEvent]) -> GraphOut:
    state: dict[str, dict[str, Any]] = {
        n: {
            "status": "pending",
            "invocations": 0,
            "started_at": None,
            "completed_at": None,
            "duration_ms": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "cost": None,
            "summary": None,
        }
        for n in GRAPH_NODES
    }
    running_order: list[str] = []
    last_seq = 0
    for ev in sorted(events, key=lambda e: e.seq):
        last_seq = max(last_seq, ev.seq)
        node = ev.node_id
        if not node or node not in state:
            continue
        s = state[node]
        payload = ev.payload or {}
        if ev.type == "agent.started":
            s["status"] = "running"
            s["invocations"] += 1
            s["started_at"] = s["started_at"] or ev.ts
            s["completed_at"] = None
            if node in running_order:
                running_order.remove(node)
            running_order.append(node)
        elif ev.type == "agent.completed":
            s["status"] = "completed"
            s["completed_at"] = ev.ts
            s["duration_ms"] = payload.get("duration_ms", s["duration_ms"])
            s["summary"] = payload.get("summary", s["summary"])
            s["tokens_in"] += int(payload.get("tokens_in") or 0)
            s["tokens_out"] += int(payload.get("tokens_out") or 0)
            if payload.get("cost_usd") is not None:
                s["cost"] = round((s["cost"] or 0.0) + float(payload["cost_usd"]), 6)
            if node in running_order:
                running_order.remove(node)
        elif ev.type == "agent.failed":
            s["status"] = "failed"
            s["completed_at"] = ev.ts
            if node in running_order:
                running_order.remove(node)
        elif ev.type == "validation.warning" and s["status"] != "failed":
            s["status"] = "warning" if s["status"] != "running" else s["status"]

    terminal = run.status in TERMINAL_RUN_STATUSES
    nodes: list[GraphNodeOut] = []
    for n in GRAPH_NODES:
        s = state[n]
        status = s["status"]
        if status == "pending" and terminal:
            status = "skipped"
        if status == "warning":
            status = "completed"  # finished, warnings are surfaced via events
        nodes.append(
            GraphNodeOut(
                id=n,
                label=n.replace("_", " ").title(),
                status=status,
                duration_ms=s["duration_ms"],
                role=n,
                invocations=s["invocations"],
                started_at=s["started_at"],
                completed_at=s["completed_at"],
                input_tokens=s["tokens_in"],
                output_tokens=s["tokens_out"],
                cost_usd=s["cost"],
                summary=s["summary"],
            )
        )
    edges = [GraphEdgeOut(**e) for e in graph_snapshot()["edges"]]
    return GraphOut(
        nodes=nodes,
        edges=edges,
        current_node=(running_order[-1] if running_order and not terminal else None),
        run_status=run.status,
        last_seq=last_seq,
    )


def build_waterfall(run: AgentRun, events: list[AgentEvent], costs_by_role: dict[str, float]) -> list[dict[str, Any]]:
    """Per-agent timeline relative to run start; overlapping spans show parallel execution."""
    origin = run.started_at
    if origin is None and events:
        origin = min(e.ts for e in events)
    spans: dict[str, dict[str, Any]] = {}
    for ev in sorted(events, key=lambda e: e.seq):
        node = ev.node_id
        if not node:
            continue
        sp = spans.setdefault(node, {"node": node, "start": None, "end": None, "attempts": 0})
        if ev.type == "agent.started":
            sp["attempts"] += 1
            sp["start"] = sp["start"] or ev.ts
        elif ev.type in {"agent.completed", "agent.failed"}:
            sp["end"] = ev.ts
    out: list[dict[str, Any]] = []
    cumulative = 0.0
    ordered = sorted(
        (s for s in spans.values() if s["start"] is not None),
        key=lambda s: (s["start"], GRAPH_NODES.index(s["node"]) if s["node"] in GRAPH_NODES else 99),
    )
    for sp in ordered:
        cost = float(costs_by_role.get(sp["node"], 0.0))
        cumulative = round(cumulative + cost, 6)
        out.append(
            {
                "node": sp["node"],
                "start_ms": _ms_between(origin, sp["start"]),
                "end_ms": _ms_between(origin, sp["end"]),
                "duration_ms": _ms_between(sp["start"], sp["end"]),
                "attempts": sp["attempts"],
                "cost_usd": round(cost, 6),
                "cumulative_cost_usd": cumulative,
            }
        )
    return out
