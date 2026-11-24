from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.common import get_owned_run, not_found
from app.auth.deps import get_current_user, require_csrf
from app.config import get_settings
from app.db.session import get_db
from app.models import BenchmarkCase, EvaluationRun, Trip, User
from app.schemas.analytics import (
    BenchmarkCaseOut,
    BenchmarkIn,
    BenchmarkOut,
    CompareIn,
    CompareOut,
    CompareRunOut,
    EvaluationCreateIn,
    EvaluationEvidenceOut,
    EvaluationMetricOut,
    EvaluationOut,
)
from app.schemas.common import Paginated
from app.schemas.runs import RunOut
from app.services.benchmark import ensure_benchmark_cases, run_benchmark
from app.services.evaluation import evaluate_run_deterministic

router = APIRouter(prefix="/evaluations", tags=["evaluations"], dependencies=[Depends(require_csrf)])

METRIC_ORDER = [
    "budget_compliance",
    "day_count_validity",
    "itinerary_completeness",
    "preference_coverage",
    "tool_success_rate",
    "error_count",
    "latency_score",
    "relevance",
    "coherence",
    "feasibility",
    "recommendation_quality",
    "unsupported_claims",
]


def _metric_sort_key(name: str) -> tuple[int, str]:
    return (METRIC_ORDER.index(name) if name in METRIC_ORDER else len(METRIC_ORDER), name)


def evaluation_to_out(
    ev: EvaluationRun, *, with_run: bool = False, with_evidence: bool = False
) -> EvaluationOut:
    metrics = sorted(ev.metrics, key=lambda m: _metric_sort_key(m.name))
    return EvaluationOut(
        id=ev.id,
        run_id=ev.run_id,
        run_public_id=ev.run.public_id if ev.run is not None else None,
        kind=ev.kind,
        label=ev.label,
        overall_score=ev.overall_score,
        status=ev.status,
        rubric_version=ev.rubric_version,
        is_demo_fixture=ev.is_demo_fixture,
        summary=ev.summary,
        judge_model=ev.judge_model,
        judge_prompt_version=ev.judge_prompt_version,
        metrics=[EvaluationMetricOut.model_validate(m) for m in metrics],
        evidence=[EvaluationEvidenceOut.model_validate(e) for e in ev.evidence] if with_evidence else [],
        created_at=ev.created_at,
        run=RunOut.model_validate(ev.run) if with_run and ev.run is not None else None,
    )


def _eval_options():
    return (
        selectinload(EvaluationRun.metrics),
        selectinload(EvaluationRun.evidence),
        selectinload(EvaluationRun.run),
    )


@router.get("", response_model=Paginated[EvaluationOut])
async def list_evaluations(
    run_id: Optional[str] = None,
    kind: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Paginated[EvaluationOut]:
    conditions = [EvaluationRun.user_id == user.id]
    if run_id:
        run = await get_owned_run(db, user, run_id)
        conditions.append(EvaluationRun.run_id == run.id)
    if kind:
        conditions.append(EvaluationRun.kind == kind)
    total = (await db.execute(select(func.count(EvaluationRun.id)).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(EvaluationRun)
            .where(*conditions)
            .options(*_eval_options())
            .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return Paginated[EvaluationOut](
        items=[evaluation_to_out(r) for r in rows], total=total, page=page, page_size=page_size
    )


@router.post("", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreateIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationOut:
    settings = get_settings()
    if payload.kind != "deterministic":
        if payload.kind == "judge" and not settings.is_demo:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Model-as-judge evaluation is not enabled in this build.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only deterministic evaluation can be run in demo mode; judge scores show 'Not evaluated'.",
        )
    run = await get_owned_run(db, user, payload.run_id)
    if run.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only completed runs can be evaluated"
        )
    trip = await db.get(Trip, run.trip_id) if run.trip_id else None
    ev = await evaluate_run_deterministic(db, user_id=user.id, run=run, trip=trip)
    await db.commit()
    fresh = (
        await db.execute(
            select(EvaluationRun)
            .where(EvaluationRun.id == ev.id)
            .options(*_eval_options())
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    return evaluation_to_out(fresh, with_run=True, with_evidence=True)


# NOTE: static paths must be declared before "/{evaluation_id}"
@router.get("/benchmark/cases", response_model=list[BenchmarkCaseOut])
async def list_benchmark_cases(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[BenchmarkCaseOut]:
    await ensure_benchmark_cases(db)
    await db.commit()
    rows = (await db.execute(select(BenchmarkCase).order_by(BenchmarkCase.created_at, BenchmarkCase.slug))).scalars()
    return [BenchmarkCaseOut.model_validate(r) for r in rows]


@router.post("/benchmark", response_model=BenchmarkOut)
async def benchmark(
    payload: Optional[BenchmarkIn] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BenchmarkOut:
    if not get_settings().is_demo:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The local benchmark only runs in AI_MODE=demo so it never incurs paid usage.",
        )
    results = await run_benchmark(db, user, (payload.case_slugs if payload else None))
    passed = sum(1 for r in results if r.passed)
    return BenchmarkOut(total=len(results), passed=passed, failed=len(results) - passed, results=results)


@router.post("/compare", response_model=CompareOut)
async def compare(
    payload: CompareIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CompareOut:
    runs = []
    seen: set[str] = set()
    for ref in payload.run_ids:
        run = await get_owned_run(db, user, ref)
        if run.id in seen:
            continue
        seen.add(run.id)
        runs.append(run)
    if len(runs) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select at least two distinct runs"
        )

    evals_by_run: dict[str, list[EvaluationRun]] = {r.id: [] for r in runs}
    rows = (
        await db.execute(
            select(EvaluationRun)
            .where(EvaluationRun.user_id == user.id, EvaluationRun.run_id.in_(list(seen)))
            .options(*_eval_options())
            .order_by(EvaluationRun.created_at.desc(), EvaluationRun.id)
        )
    ).scalars().all()
    for ev in rows:
        evals_by_run[ev.run_id].append(ev)

    run_outs: list[CompareRunOut] = []
    units: dict[str, str] = {}
    provenance: dict[str, set[str]] = {}
    rubric_versions: set[str] = set()
    any_fixture = False
    for run in runs:
        metrics: dict[str, Optional[float]] = {}
        overall_by_kind: dict[str, Optional[float]] = {}
        for ev in evals_by_run[run.id]:  # newest first: first value per metric wins
            rubric_versions.add(ev.rubric_version)
            any_fixture = any_fixture or ev.is_demo_fixture
            overall_by_kind.setdefault(ev.kind, ev.overall_score)
            for m in ev.metrics:
                if m.name not in metrics:
                    metrics[m.name] = m.value
                    units.setdefault(m.name, m.unit)
                    provenance.setdefault(m.name, set()).add(m.provenance)
        run_outs.append(
            CompareRunOut(
                run_id=run.id,
                public_id=run.public_id,
                status=run.status,
                model_name=run.model_name,
                ai_mode=run.ai_mode,
                wall_time_ms=run.wall_time_ms,
                total_cost_usd=run.total_cost_usd,
                input_tokens=run.input_tokens,
                output_tokens=run.output_tokens,
                evaluations=[evaluation_to_out(e) for e in evals_by_run[run.id]],
                metrics=metrics,
                overall_by_kind=overall_by_kind,
                is_demo_fixture=any(e.is_demo_fixture for e in evals_by_run[run.id]),
            )
        )

    names = sorted({n for r in run_outs for n in r.metrics}, key=_metric_sort_key)
    baseline = run_outs[0]
    deltas: dict[str, dict[str, Optional[float]]] = {}
    missing: list[dict[str, str]] = []
    for name in names:
        deltas[name] = {}
        for r in run_outs:
            if name not in r.metrics or r.metrics[name] is None:
                missing.append({"run_id": r.run_id, "public_id": r.public_id, "metric": name})
            if r.run_id == baseline.run_id:
                continue
            a, b = baseline.metrics.get(name), r.metrics.get(name)
            deltas[name][r.run_id] = round(b - a, 4) if a is not None and b is not None else None

    notes: list[str] = []
    if any_fixture:
        notes.append("Includes 'Sample evaluation (demo)' fixtures: seeded historical scores, not live judgements.")
    if len(rubric_versions) > 1:
        notes.append("Runs were scored with different rubric versions; compare with care.")
    no_eval = [r.public_id for r in run_outs if not r.metrics]
    if no_eval:
        notes.append(f"No evaluation recorded yet for: {', '.join(no_eval)} (shown as Not evaluated).")
    notes.append("Deltas are measured against the first selected run.")

    return CompareOut(
        baseline_run_id=baseline.run_id,
        runs=run_outs,
        metric_names=names,
        metric_units=units,
        metric_provenance={k: ",".join(sorted(v)) for k, v in provenance.items()},
        deltas=deltas,
        missing=missing,
        notes=notes,
    )


@router.get("/{evaluation_id}", response_model=EvaluationOut)
async def get_evaluation(
    evaluation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> EvaluationOut:
    ev = (
        await db.execute(
            select(EvaluationRun)
            .where(EvaluationRun.id == evaluation_id, EvaluationRun.user_id == user.id)
            .options(*_eval_options())
        )
    ).scalar_one_or_none()
    if ev is None:
        raise not_found("Evaluation")
    return evaluation_to_out(ev, with_run=True, with_evidence=True)
