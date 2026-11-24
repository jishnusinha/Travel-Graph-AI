from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, EvaluationEvidence, EvaluationMetric, EvaluationRun, Trip


def compute_overall_score(metrics_spec: list[tuple[str, float, str, float]]) -> float:
    """Weighted overall on a 0-5 scale from (name, value, unit, weight) tuples.

    Percent metrics are scaled 0-100 -> 0-5, count metrics are inverted (0 errors = 5),
    and `/5` metrics are used as-is. Only meaningful when weights sum to ~1.0.
    """
    overall = 0.0
    for _, value, unit, weight in metrics_spec:
        if unit == "count":
            overall += weight * max(0.0, 1.0 - min(value, 5) / 5) * 5
        elif unit == "%":
            overall += weight * (value / 100) * 5
        else:
            overall += weight * value
    return round(overall, 2)


async def evaluate_run_deterministic(
    db: AsyncSession,
    *,
    user_id: str,
    run: AgentRun,
    trip: Trip | None = None,
) -> EvaluationRun:
    plan = run.final_plan or {}
    budget = plan.get("budget_breakdown") or (trip.budget_breakdown if trip else {}) or {}
    days = plan.get("days") or []
    trip_budget = int(plan.get("budget_inr") or (trip.budget_inr if trip else 0) or 0)
    estimated = int(plan.get("estimated_cost_inr") or budget.get("total") or 0)
    expected_days = 0
    if plan.get("start_date") and plan.get("end_date"):
        from datetime import date

        try:
            s = date.fromisoformat(plan["start_date"])
            e = date.fromisoformat(plan["end_date"])
            expected_days = (e - s).days + 1
        except ValueError:
            expected_days = len(days)
    else:
        expected_days = len(days)

    findings = plan.get("validation_findings") or []
    errors = [f for f in findings if f.get("severity") == "error"]
    day_ok = 1.0 if expected_days == 0 or len(days) == expected_days else 0.0
    budget_ok = 1.0 if trip_budget == 0 or estimated <= trip_budget else max(0.0, 1 - (estimated - trip_budget) / max(trip_budget, 1))
    completeness = 1.0 if days and all(d.get("activities") for d in days) else 0.5
    preference = 0.9 if (plan.get("destination") and trip_budget) else 0.5
    tool_success = 1.0 if run.status == "completed" else 0.0
    latency_score = 1.0 if run.wall_time_ms and run.wall_time_ms < 30000 else 0.7

    metrics_spec = [
        ("budget_compliance", round(budget_ok * 100, 1), "%", 0.25),
        ("day_count_validity", round(day_ok * 100, 1), "%", 0.15),
        ("itinerary_completeness", round(completeness * 5, 2), "/5", 0.2),
        ("preference_coverage", round(preference * 5, 2), "/5", 0.15),
        ("tool_success_rate", round(tool_success * 100, 1), "%", 0.1),
        ("error_count", float(len(errors)), "count", 0.05),
        ("latency_score", round(latency_score * 5, 2), "/5", 0.1),
    ]

    overall = compute_overall_score(metrics_spec)

    ev = EvaluationRun(
        user_id=user_id,
        run_id=run.id,
        kind="deterministic",
        label=f"Deterministic eval · {run.public_id}",
        overall_score=overall,
        status="completed",
        rubric_version="travelplan-v1",
        is_demo_fixture=False,
        summary="Scores computed from trip/run fields using deterministic rubrics. Not a model judge.",
    )
    db.add(ev)
    await db.flush()
    for name, value, unit, weight in metrics_spec:
        db.add(
            EvaluationMetric(
                evaluation_id=ev.id,
                name=name,
                value=value,
                unit=unit,
                weight=weight,
                provenance="deterministic",
                status="ok",
                details={"method": "rule-based"},
            )
        )
    db.add(
        EvaluationEvidence(
            evaluation_id=ev.id,
            metric_name="budget_compliance",
            snippet=f"Estimated ₹{estimated} vs budget ₹{trip_budget}",
            source_ref=f"run:{run.public_id}",
        )
    )
    await db.flush()
    return ev


BENCHMARK_CASES: list[dict[str, Any]] = [
    {"slug": "goa-budget", "title": "Goa budget trip", "prompt": "Plan a 5-day Goa trip for two under ₹35,000 with beaches and local food.", "expected": {"destination": "Goa", "days": 5}, "tags": ["goa", "budget"]},
    {"slug": "manali-family", "title": "Manali family", "prompt": "Plan a 6-day Manali family trip for 4 with mountains and nature.", "expected": {"destination": "Manali", "days": 6}, "tags": ["manali", "family"]},
    {"slug": "udaipur-heritage", "title": "Udaipur heritage", "prompt": "4-day Udaipur heritage trip for 2 under ₹40,000.", "expected": {"destination": "Udaipur", "days": 4}, "tags": ["udaipur"]},
    {"slug": "kerala-nature", "title": "Kerala nature", "prompt": "5-day Kerala backwaters nature trip for 2.", "expected": {"destination": "Kerala", "days": 5}, "tags": ["kerala"]},
    {"slug": "solo-city", "title": "Solo city break", "prompt": "3-day Jaipur solo city break under ₹20,000.", "expected": {"destination": "Jaipur", "days": 3}, "tags": ["jaipur", "solo"]},
    {"slug": "budget-conflict", "title": "Budget conflict", "prompt": "Plan a 5-day Goa luxury trip for 2 under ₹8,000.", "expected": {"budget_tight": True}, "tags": ["edge"]},
    {"slug": "missing-destination", "title": "Missing destination", "prompt": "Plan a relaxing 5-day trip for two under ₹35,000.", "expected": {"needs_destination": True}, "tags": ["edge"]},
    {"slug": "unrealistic-dates", "title": "Unrealistic dates", "prompt": "Plan Goa from 2027-01-16 to 2027-01-12 for 2.", "expected": {"invalid_dates": True}, "tags": ["edge"]},
]
