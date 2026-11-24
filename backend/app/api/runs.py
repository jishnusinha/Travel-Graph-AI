from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.api.common import get_owned_run, get_owned_trip, spawn_run
from app.auth.deps import get_current_user, require_csrf
from app.db.session import SessionLocal, get_db
from app.models import (
    AgentEvent,
    AgentRun,
    CostLineItem,
    ModelInvocation,
    ToolInvocation,
    Trip,
    User,
)
from app.observability.events import event_bus
from app.schemas.common import MessageOut, Paginated
from app.schemas.runs import (
    AgentEventOut,
    GraphOut,
    NodeDetailOut,
    RunCreateIn,
    RunListItem,
    RunOut,
)
from app.services.run_executor import TERMINAL_EVENT_TYPES, create_run
from app.services.run_views import TERMINAL_RUN_STATUSES, build_graph

router = APIRouter(prefix="/runs", tags=["runs"], dependencies=[Depends(require_csrf)])

ACTIVE_STATUSES = {"pending", "running"}


async def _events_for(db: AsyncSession, run_id: str, after_seq: int = 0, limit: int = 5000) -> list[AgentEvent]:
    return list(
        (
            await db.execute(
                select(AgentEvent)
                .where(AgentEvent.run_id == run_id, AgentEvent.seq > after_seq)
                .order_by(AgentEvent.seq)
                .limit(limit)
            )
        ).scalars()
    )


@router.get("", response_model=Paginated[RunListItem])
async def list_runs(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    trip_id: Optional[str] = None,
    q: Optional[str] = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Paginated[RunListItem]:
    conditions = [AgentRun.user_id == user.id]
    if status_filter and status_filter != "all":
        conditions.append(AgentRun.status == status_filter)
    if trip_id:
        conditions.append(AgentRun.trip_id == trip_id)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        conditions.append(
            func.lower(AgentRun.prompt).like(like) | func.lower(AgentRun.public_id).like(like)
        )
    total = (await db.execute(select(func.count(AgentRun.id)).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(AgentRun, Trip.title)
            .outerjoin(Trip, AgentRun.trip_id == Trip.id)
            .where(*conditions)
            .order_by(AgentRun.created_at.desc(), AgentRun.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    items = []
    for run, trip_title in rows:
        item = RunListItem.model_validate(run)
        item.trip_title = trip_title
        items.append(item)
    return Paginated[RunListItem](items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def create_agent_run(
    payload: RunCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRun:
    revision = 1
    trip: Trip | None = None
    if payload.trip_id:
        trip = await get_owned_trip(db, user, payload.trip_id)
        revision = (
            await db.execute(select(func.count(AgentRun.id)).where(AgentRun.trip_id == trip.id))
        ).scalar_one() + 1
    request_payload = payload.model_dump(exclude={"trip_id"})
    run = await create_run(
        db,
        user_id=user.id,
        payload=request_payload,
        trip_id=trip.id if trip else None,
        revision_number=int(revision),
    )
    if trip is not None and trip.status == "draft":
        trip.status = "in_progress"
    await db.commit()
    spawn_run(run.id)
    return run


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> AgentRun:
    return await get_owned_run(db, user, run_id)


@router.delete("/{run_id}", response_model=MessageOut)
async def delete_run(
    run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> MessageOut:
    run = await get_owned_run(db, user, run_id)
    if run.status in ACTIVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete a run that is still active")
    await db.delete(run)
    await db.commit()
    return MessageOut(message="Run deleted")


@router.get("/{run_id}/events", response_model=list[AgentEventOut])
async def list_events(
    run_id: str,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=2000, ge=1, le=10000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentEvent]:
    run = await get_owned_run(db, user, run_id)
    return await _events_for(db, run.id, after_seq, limit)


@router.get("/{run_id}/graph", response_model=GraphOut)
async def run_graph(
    run_id: str,
    up_to_seq: Optional[int] = Query(default=None, ge=0, description="Reconstruct the graph as of this event (replay)"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GraphOut:
    run = await get_owned_run(db, user, run_id)
    events = await _events_for(db, run.id)
    if up_to_seq is not None:
        events = [e for e in events if e.seq <= up_to_seq]
    graph = build_graph(run, events)
    if up_to_seq is not None and events and events[-1].type not in TERMINAL_EVENT_TYPES:
        # Mid-replay: nodes that have not started yet are pending, not skipped
        for n in graph.nodes:
            if n.status == "skipped":
                n.status = "pending"
        graph.run_status = "running"
    return graph


@router.get("/{run_id}/nodes/{node_id}", response_model=NodeDetailOut)
async def node_detail(
    run_id: str,
    node_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeDetailOut:
    """Inspector payload for one graph node: its events, model/tool calls, costs, errors."""
    run = await get_owned_run(db, user, run_id)
    events = [e for e in await _events_for(db, run.id) if e.node_id == node_id]
    graph = build_graph(run, events)
    node = next((n for n in graph.nodes if n.id == node_id), None)
    if node is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    models = (
        await db.execute(select(ModelInvocation).where(ModelInvocation.run_id == run.id, ModelInvocation.node_id == node_id))
    ).scalars().all()
    tools = (
        await db.execute(select(ToolInvocation).where(ToolInvocation.run_id == run.id, ToolInvocation.node_id == node_id))
    ).scalars().all()
    costs = (
        await db.execute(select(CostLineItem).where(CostLineItem.run_id == run.id, CostLineItem.agent_role == node_id))
    ).scalars().all()
    errors = [
        str((e.payload or {}).get("error") or (e.payload or {}).get("message") or "")
        for e in events
        if e.type == "agent.failed" or (e.type == "validation.warning")
    ]
    return NodeDetailOut(
        node_id=node_id,
        status=node.status,
        events=[AgentEventOut.model_validate(e) for e in events],
        model_invocations=[
            {
                "provider": m.provider,
                "model": m.model,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
                "cached_tokens": m.cached_tokens,
                "estimated_cost_usd": m.estimated_cost_usd,
                "cost_status": m.cost_status,
                "duration_ms": m.duration_ms,
            }
            for m in models
        ],
        tool_invocations=[
            {
                "tool_name": t.tool_name,
                "status": t.status,
                "duration_ms": t.duration_ms,
                "fee_usd": t.fee_usd,
                "provenance": t.provenance,
                "input_summary": t.input_summary,
                "output_summary": t.output_summary,
            }
            for t in tools
        ],
        cost_items=[
            {
                "category": c.category,
                "model": c.model,
                "tool_name": c.tool_name,
                "amount_usd": c.amount_usd,
                "tokens_in": c.tokens_in,
                "tokens_out": c.tokens_out,
                "provenance": c.provenance,
            }
            for c in costs
        ],
        errors=[e for e in errors if e],
    )


# ----------------------------------------------------------------------------- SSE
def _sse(ev: dict[str, Any]) -> dict[str, str]:
    return {"id": str(ev["seq"]), "data": json.dumps(ev, default=str)}


def _event_dict(row: AgentEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "seq": row.seq,
        "ts": row.ts.isoformat(),
        "type": row.type,
        "node_id": row.node_id,
        "status": row.status,
        "payload": row.payload or {},
    }


async def _stream_events(request: Request, run_id: str, cursor: int) -> AsyncIterator[dict[str, str]]:
    """Replay persisted events after `cursor`, then follow live ones; the DB is the source of truth.

    The in-process bus only shortens latency. Bus events are accepted solely when they are the
    next contiguous seq, so a client can never observe a gap or out-of-order events.
    """
    last = cursor
    queue = await event_bus.subscribe(run_id)
    incoming: list[dict[str, Any]] = []
    try:
        while True:
            terminal_seen = False
            async with SessionLocal() as db:
                rows = await _events_for(db, run_id, last, limit=1000)
                run_status = (
                    await db.execute(select(AgentRun.status).where(AgentRun.id == run_id))
                ).scalar_one_or_none()
            for row in rows:
                if row.seq <= last:
                    continue
                yield _sse(_event_dict(row))
                last = row.seq
                terminal_seen = terminal_seen or row.type in TERMINAL_EVENT_TYPES
            for ev in sorted(incoming, key=lambda e: e["seq"]):
                if ev["seq"] == last + 1:
                    yield _sse(ev)
                    last = ev["seq"]
                    terminal_seen = terminal_seen or ev["type"] in TERMINAL_EVENT_TYPES
            incoming = []

            if run_status is None:  # run deleted mid-stream
                break
            if terminal_seen or (not rows and run_status in TERMINAL_RUN_STATUSES):
                yield {"event": "end", "data": json.dumps({"status": run_status, "last_seq": last})}
                break
            if await request.is_disconnected():
                break
            if len(rows) >= 1000:
                continue  # more backlog to page through before waiting
            try:
                incoming.append(await asyncio.wait_for(queue.get(), timeout=1.0))
                while not queue.empty():
                    incoming.append(queue.get_nowait())
            except asyncio.TimeoutError:
                pass
    finally:
        await event_bus.unsubscribe(run_id, queue)


@router.get("/{run_id}/stream")
async def stream_run(
    run_id: str,
    request: Request,
    after_seq: Optional[int] = Query(default=None, ge=0),
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    """Server-Sent Events. Resume with `Last-Event-ID` (set automatically by EventSource) or `?after_seq=`."""
    run = await get_owned_run(db, user, run_id)
    cursor = after_seq or 0
    if after_seq is None and last_event_id and last_event_id.isdigit():
        cursor = int(last_event_id)
    return EventSourceResponse(
        _stream_events(request, run.id, cursor),
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        ping=15,
    )
