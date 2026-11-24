from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.common import get_owned_run
from app.auth.deps import get_current_user, require_csrf
from app.db.base import utcnow
from app.db.session import get_db
from app.graph.workflow import GRAPH_NODES
from app.models import AgentEvent, AgentRun, CostLineItem, EvaluationRun, ToolInvocation, Trip, User
from app.schemas.analytics import CostRunDetailOut, CostSummaryOut, DashboardOut
from app.schemas.runs import RunOut
from app.services.accounting import reconciles
from app.services.run_views import build_waterfall
from app.services.trip_service import day_count_subquery, serialize_trip_list_item

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_csrf)])


def _agent_sort_key(agent: str) -> tuple[int, str]:
    return (GRAPH_NODES.index(agent) if agent in GRAPH_NODES else len(GRAPH_NODES), agent)


def _provenance(values: set[str]) -> str:
    if not values:
        return "demo"
    return next(iter(values)) if len(values) == 1 else "mixed"


# ------------------------------------------------------------------------- dashboard
@router.get("/dashboard", response_model=DashboardOut)
async def dashboard(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> DashboardOut:
    counts = dict(
        (
            await db.execute(
                select(Trip.status, func.count(Trip.id)).where(Trip.user_id == user.id).group_by(Trip.status)
            )
        ).all()
    )
    total_trips = sum(counts.values())
    agent_runs = (
        await db.execute(select(func.count(AgentRun.id)).where(AgentRun.user_id == user.id))
    ).scalar_one()
    avg_quality = (
        await db.execute(
            select(func.avg(EvaluationRun.overall_score)).where(
                EvaluationRun.user_id == user.id,
                EvaluationRun.kind == "deterministic",
                EvaluationRun.overall_score.is_not(None),
            )
        )
    ).scalar_one_or_none()
    total_cost = (
        await db.execute(
            select(func.coalesce(func.sum(AgentRun.total_cost_usd), 0.0)).where(AgentRun.user_id == user.id)
        )
    ).scalar_one()
    has_fixture = (
        await db.execute(
            select(func.count(EvaluationRun.id)).where(
                EvaluationRun.user_id == user.id, EvaluationRun.is_demo_fixture.is_(True)
            )
        )
    ).scalar_one()

    recent_rows = (
        await db.execute(
            select(Trip, day_count_subquery().label("day_count"))
            .where(Trip.user_id == user.id)
            .order_by(Trip.updated_at.desc(), Trip.id)
            .limit(4)
        )
    ).all()
    recent = [serialize_trip_list_item(t, int(n or 0)) for t, n in recent_rows]

    activity_rows = (
        await db.execute(
            select(AgentRun, Trip.title)
            .outerjoin(Trip, AgentRun.trip_id == Trip.id)
            .where(AgentRun.user_id == user.id)
            .order_by(AgentRun.created_at.desc())
            .limit(5)
        )
    ).all()
    activity = [
        {
            "run_id": r.id,
            "public_id": r.public_id,
            "trip_id": r.trip_id,
            "trip_title": title,
            "status": r.status,
            "model_name": r.model_name,
            "wall_time_ms": r.wall_time_ms,
            "total_cost_usd": r.total_cost_usd,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "cost_provenance": r.cost_provenance,
        }
        for r, title in activity_rows
    ]
    first_name = (user.full_name or "Traveler").split()[0]
    return DashboardOut(
        greeting_name=first_name,
        trips_planned=total_trips,
        trips_completed=counts.get("completed", 0),
        trips_in_progress=counts.get("in_progress", 0),
        trips_draft=counts.get("draft", 0),
        agent_runs=agent_runs,
        avg_plan_quality=round(float(avg_quality), 2) if avg_quality is not None else None,
        total_ai_cost_usd=round(float(total_cost), 6),
        recent_trips=recent,
        agent_activity=activity,
        provenance="database (avg quality: deterministic scores out of 5"
        + ("; includes Sample evaluation (demo) fixtures)" if has_fixture else ")"),
    )


# ------------------------------------------------------------------------- costs (aggregate)
async def _filtered_items(
    db: AsyncSession,
    user: User,
    *,
    days: int,
    start: Optional[date],
    end: Optional[date],
    model: Optional[str],
    agent: Optional[str],
    run_ref: Optional[str],
) -> tuple[list[Any], datetime, datetime]:
    now = utcnow()
    if start or end:
        start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc) if start else datetime(2000, 1, 1, tzinfo=timezone.utc)
        end_dt = datetime.combine(end, time.max, tzinfo=timezone.utc) if end else now
    elif days > 0:
        start_dt, end_dt = now - timedelta(days=days), now
    else:
        start_dt, end_dt = datetime(2000, 1, 1, tzinfo=timezone.utc), now
    if start_dt > end_dt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start must not be after end")

    conditions = [
        CostLineItem.user_id == user.id,
        CostLineItem.occurred_at >= start_dt,
        CostLineItem.occurred_at <= end_dt,
    ]
    if model:
        conditions.append(AgentRun.model_name == model)
    if agent:
        conditions.append(CostLineItem.agent_role == agent)
    if run_ref:
        run = await get_owned_run(db, user, run_ref)
        conditions.append(CostLineItem.run_id == run.id)
    rows = (
        await db.execute(
            select(
                CostLineItem.run_id,
                CostLineItem.category,
                CostLineItem.agent_role,
                CostLineItem.model,
                CostLineItem.tool_name,
                CostLineItem.amount_usd,
                CostLineItem.tokens_in,
                CostLineItem.tokens_out,
                CostLineItem.provenance,
                CostLineItem.occurred_at,
                AgentRun.public_id,
                AgentRun.status,
                AgentRun.model_name,
            )
            .join(AgentRun, AgentRun.id == CostLineItem.run_id)
            .where(*conditions)
            .order_by(CostLineItem.occurred_at, CostLineItem.id)
        )
    ).all()
    return list(rows), start_dt, end_dt


@router.get("/costs", response_model=CostSummaryOut)
async def costs(
    days: int = Query(default=30, ge=0, le=3650, description="Rolling window; 0 = all time"),
    start: Optional[date] = None,
    end: Optional[date] = None,
    model: Optional[str] = None,
    agent: Optional[str] = None,
    run_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CostSummaryOut:
    rows, start_dt, end_dt = await _filtered_items(
        db, user, days=days, start=start, end=end, model=model, agent=agent, run_ref=run_id
    )
    total = model_total = tool_total = 0.0
    tin = tout = 0
    by_agent: dict[str, dict[str, Any]] = {}
    by_model: dict[str, dict[str, Any]] = {}
    per_run: dict[str, dict[str, Any]] = {}
    per_day: dict[date, dict[str, Any]] = defaultdict(
        lambda: {"cost_usd": 0.0, "model_cost_usd": 0.0, "tool_cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0, "runs": set()}
    )
    provenances: set[str] = set()
    for r in rows:
        amount = float(r.amount_usd or 0.0)
        total += amount
        provenances.add(r.provenance)
        tin += r.tokens_in
        tout += r.tokens_out
        is_tool = r.category == "tool"
        model_total += 0.0 if is_tool else amount
        tool_total += amount if is_tool else 0.0

        a = by_agent.setdefault(
            r.agent_role or "unattributed",
            {"agent": r.agent_role or "unattributed", "cost_usd": 0.0, "model_cost_usd": 0.0, "tool_cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0},
        )
        a["cost_usd"] += amount
        a["model_cost_usd" if not is_tool else "tool_cost_usd"] += amount
        a["tokens_in"] += r.tokens_in
        a["tokens_out"] += r.tokens_out

        model_key = "tools (no model)" if is_tool else (r.model or "unknown")
        m = by_model.setdefault(
            model_key,
            {"model": model_key, "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0, "calls": 0, "is_tool": is_tool},
        )
        m["cost_usd"] += amount
        m["tokens_in"] += r.tokens_in
        m["tokens_out"] += r.tokens_out
        m["calls"] += 1

        pr = per_run.setdefault(r.run_id, {"status": r.status, "cost": 0.0})
        pr["cost"] += amount

        day = r.occurred_at.astimezone(timezone.utc).date()
        d = per_day[day]
        d["cost_usd"] += amount
        d["model_cost_usd" if not is_tool else "tool_cost_usd"] += amount
        d["tokens_in"] += r.tokens_in
        d["tokens_out"] += r.tokens_out
        d["runs"].add(r.run_id)

    completed = [v["cost"] for v in per_run.values() if v["status"] == "completed"]
    avg = (sum(completed) / len(completed)) if completed else 0.0

    # Zero-filled daily trend so charts show gaps honestly
    first_day = start_dt.date() if (start or end or days > 0) else (min(per_day) if per_day else end_dt.date())
    trend = []
    cursor = first_day
    while cursor <= end_dt.date():
        d = per_day.get(cursor)
        trend.append(
            {
                "date": cursor.isoformat(),
                "cost_usd": round(d["cost_usd"], 6) if d else 0.0,
                "model_cost_usd": round(d["model_cost_usd"], 6) if d else 0.0,
                "tool_cost_usd": round(d["tool_cost_usd"], 6) if d else 0.0,
                "tokens": (d["tokens_in"] + d["tokens_out"]) if d else 0,
                "runs": len(d["runs"]) if d else 0,
            }
        )
        cursor += timedelta(days=1)

    unpriced = (
        await db.execute(
            select(func.count(AgentRun.id)).where(
                AgentRun.user_id == user.id,
                AgentRun.created_at >= start_dt,
                AgentRun.created_at <= end_dt,
                (AgentRun.input_tokens + AgentRun.output_tokens) > 0,
                AgentRun.total_cost_usd <= 0,
            )
        )
    ).scalar_one()

    def _round(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for it in items:
            for k in ("cost_usd", "model_cost_usd", "tool_cost_usd"):
                if k in it:
                    it[k] = round(it[k], 6)
            it["share_pct"] = round(100 * it["cost_usd"] / total, 1) if total else 0.0
        return items

    return CostSummaryOut(
        total_cost_usd=round(total, 6),
        total_tokens=tin + tout,
        input_tokens=tin,
        output_tokens=tout,
        avg_cost_per_run_usd=round(avg, 6),
        by_agent=_round(sorted(by_agent.values(), key=lambda x: _agent_sort_key(x["agent"]))),
        by_model=_round(sorted(by_model.values(), key=lambda x: -x["cost_usd"])),
        trend=trend,
        provenance=_provenance(provenances),
        model_cost_usd=round(model_total, 6),
        tool_cost_usd=round(tool_total, 6),
        run_count=len(per_run),
        unpriced_run_count=int(unpriced),
        filters={
            "days": days,
            "start": start_dt.date().isoformat(),
            "end": end_dt.date().isoformat(),
            "model": model,
            "agent": agent,
            "run_id": run_id,
        },
    )


def _csv_response(rows: list[dict[str, Any]], filename: str) -> Response:
    buf = io.StringIO()
    fields = [
        "run_public_id", "occurred_at", "category", "agent_role", "model", "tool_name",
        "amount_usd", "tokens_in", "tokens_out", "provenance",
    ]
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in fields})
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _row_dict(r: Any) -> dict[str, Any]:
    return {
        "run_public_id": r.public_id,
        "occurred_at": r.occurred_at.isoformat(),
        "category": r.category,
        "agent_role": r.agent_role,
        "model": r.model or "",
        "tool_name": r.tool_name or "",
        "amount_usd": f"{float(r.amount_usd or 0.0):.6f}",
        "tokens_in": r.tokens_in,
        "tokens_out": r.tokens_out,
        "provenance": r.provenance,
    }


@router.get("/costs/export")
async def export_costs(
    days: int = Query(default=30, ge=0, le=3650),
    start: Optional[date] = None,
    end: Optional[date] = None,
    model: Optional[str] = None,
    agent: Optional[str] = None,
    run_id: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    rows, _, _ = await _filtered_items(
        db, user, days=days, start=start, end=end, model=model, agent=agent, run_ref=run_id
    )
    return _csv_response([_row_dict(r) for r in rows], "travelgraph-costs.csv")


# ------------------------------------------------------------------------- costs (single run)
async def _run_cost_rows(db: AsyncSession, run: AgentRun) -> list[CostLineItem]:
    return list(
        (
            await db.execute(
                select(CostLineItem)
                .where(CostLineItem.run_id == run.id)
                .order_by(CostLineItem.occurred_at, CostLineItem.id)
            )
        ).scalars()
    )


@router.get("/costs/runs/{run_id}", response_model=CostRunDetailOut)
async def run_cost_detail(
    run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> CostRunDetailOut:
    run = await get_owned_run(db, user, run_id)
    items = await _run_cost_rows(db, run)
    events = list(
        (await db.execute(select(AgentEvent).where(AgentEvent.run_id == run.id).order_by(AgentEvent.seq))).scalars()
    )
    tool_rows = list(
        (await db.execute(select(ToolInvocation).where(ToolInvocation.run_id == run.id))).scalars()
    )

    total = sum(float(i.amount_usd or 0.0) for i in items)
    tin = sum(i.tokens_in for i in items)
    tout = sum(i.tokens_out for i in items)
    by_agent: dict[str, dict[str, Any]] = {}
    by_model: dict[str, dict[str, Any]] = {}
    for i in items:
        is_tool = i.category == "tool"
        a = by_agent.setdefault(
            i.agent_role or "unattributed",
            {"agent": i.agent_role or "unattributed", "cost_usd": 0.0, "model_cost_usd": 0.0, "tool_cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0},
        )
        a["cost_usd"] += float(i.amount_usd or 0.0)
        a["tool_cost_usd" if is_tool else "model_cost_usd"] += float(i.amount_usd or 0.0)
        a["tokens_in"] += i.tokens_in
        a["tokens_out"] += i.tokens_out
        key = "tools (no model)" if is_tool else (i.model or "unknown")
        m = by_model.setdefault(key, {"model": key, "cost_usd": 0.0, "tokens_in": 0, "tokens_out": 0, "calls": 0})
        m["cost_usd"] += float(i.amount_usd or 0.0)
        m["tokens_in"] += i.tokens_in
        m["tokens_out"] += i.tokens_out
        m["calls"] += 1
    for coll in (by_agent, by_model):
        for v in coll.values():
            for k in ("cost_usd", "model_cost_usd", "tool_cost_usd"):
                if k in v:
                    v[k] = round(v[k], 6)
            v["share_pct"] = round(100 * v["cost_usd"] / total, 1) if total else 0.0

    tools: dict[tuple[str, str], dict[str, Any]] = {}
    for t in tool_rows:
        entry = tools.setdefault(
            (t.node_id, t.tool_name),
            {"tool_name": t.tool_name, "node_id": t.node_id, "calls": 0, "fee_usd": 0.0, "duration_ms": 0, "provenance": t.provenance, "failed": 0},
        )
        entry["calls"] += 1
        entry["fee_usd"] = round(entry["fee_usd"] + float(t.fee_usd or 0.0), 6)
        entry["duration_ms"] += t.duration_ms
        entry["failed"] += 1 if t.status != "succeeded" else 0

    costs_by_role = {a["agent"]: a["cost_usd"] for a in by_agent.values()}
    return CostRunDetailOut(
        run=RunOut.model_validate(run),
        line_items=[
            {
                "category": i.category,
                "agent_role": i.agent_role,
                "model": i.model,
                "tool_name": i.tool_name,
                "amount_usd": i.amount_usd,
                "tokens_in": i.tokens_in,
                "tokens_out": i.tokens_out,
                "provenance": i.provenance,
                "occurred_at": i.occurred_at.isoformat(),
            }
            for i in items
        ],
        by_agent=sorted(by_agent.values(), key=lambda x: _agent_sort_key(x["agent"])),
        by_model=sorted(by_model.values(), key=lambda x: -x["cost_usd"]),
        tools=list(tools.values()),
        waterfall=build_waterfall(run, events, costs_by_role),
        provenance=_provenance({i.provenance for i in items}),
        wall_time_ms=run.wall_time_ms,
        reconciliation={
            "line_items_total_usd": round(total, 6),
            "run_total_usd": run.total_cost_usd,
            "difference_usd": round(total - run.total_cost_usd, 6),
            "reconciled": reconciles(run.total_cost_usd, total),
            "tokens_in_items": tin,
            "tokens_out_items": tout,
            "tokens_reconciled": tin == run.input_tokens and tout == run.output_tokens,
        },
    )


@router.get("/costs/runs/{run_id}/export")
async def export_run_costs(
    run_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Response:
    run = await get_owned_run(db, user, run_id)
    items = await _run_cost_rows(db, run)

    class _R:  # adapt ORM rows to the shared CSV row shape
        def __init__(self, i: CostLineItem) -> None:
            self.public_id = run.public_id
            self.occurred_at = i.occurred_at
            self.category = i.category
            self.agent_role = i.agent_role
            self.model = i.model
            self.tool_name = i.tool_name
            self.amount_usd = i.amount_usd
            self.tokens_in = i.tokens_in
            self.tokens_out = i.tokens_out
            self.provenance = i.provenance

    return _csv_response([_row_dict(_R(i)) for i in items], f"travelgraph-{run.public_id}-costs.csv")
