from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, BenchmarkCase, User
from app.providers.llm import demo_latency_override
from app.schemas.analytics import BenchmarkResultItem
from app.services.evaluation import BENCHMARK_CASES, evaluate_run_deterministic
from app.services.run_executor import create_run, execute_run

_NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}


async def ensure_benchmark_cases(db: AsyncSession) -> int:
    """Upsert BENCHMARK_CASES by slug. Returns the number of rows inserted."""
    existing = {c.slug: c for c in (await db.execute(select(BenchmarkCase))).scalars()}
    created = 0
    for case in BENCHMARK_CASES:
        row = existing.get(case["slug"])
        if row is None:
            db.add(
                BenchmarkCase(
                    slug=case["slug"],
                    title=case["title"],
                    prompt=case["prompt"],
                    expected=case["expected"],
                    tags=case["tags"],
                )
            )
            created += 1
        else:
            row.title, row.prompt = case["title"], case["prompt"]
            row.expected, row.tags = case["expected"], case["tags"]
    await db.flush()
    return created


def payload_from_prompt(prompt: str) -> dict[str, Any]:
    """Turn a benchmark prompt into structured request fields (budget, travelers)."""
    budget = 35000
    m = re.search(r"₹\s?([\d,]+)", prompt)
    if m:
        budget = int(m.group(1).replace(",", ""))
    travelers = 2
    low = prompt.lower()
    if "solo" in low:
        travelers = 1
    else:
        m = re.search(r"\bfor\s+(\d+|one|two|three|four|five|six)\b", low)
        if m:
            raw = m.group(1)
            travelers = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]
    return {"prompt": prompt, "travelers": travelers, "budget_inr": budget, "origin": "Kolkata, India"}


def evaluate_case(case: BenchmarkCase, run: AgentRun) -> tuple[list[dict[str, Any]], list[str]]:
    plan = run.final_plan or {}
    expected = case.expected or {}
    checks: list[dict[str, Any]] = []
    flags: list[str] = []

    def add(name: str, expected_value: Any, actual: Any, ok: bool) -> None:
        checks.append({"check": name, "expected": expected_value, "actual": actual, "passed": bool(ok)})

    clarification = (run.error_message or "").lower() if run.status == "needs_clarification" else ""
    if "destination" in expected:
        actual = str(plan.get("destination") or "")
        add("destination", expected["destination"], actual, expected["destination"].lower() in actual.lower())
    if "days" in expected:
        actual_days = len(plan.get("days") or [])
        add("day_count", expected["days"], actual_days, actual_days == expected["days"])
    if expected.get("budget_tight"):
        findings = plan.get("validation_findings") or []
        over = int(plan.get("estimated_cost_inr") or 0) > int(plan.get("budget_inr") or 0)
        flagged = any(f.get("code") == "budget_exceeded" for f in findings)
        add("budget_conflict_flagged", True, flagged, over and flagged)
        if flagged:
            flags.append("budget_exceeded")
    if expected.get("needs_destination"):
        add("asks_for_destination", True, "destination" in clarification, "destination" in clarification)
        flags.append("needs_clarification")
    if expected.get("invalid_dates"):
        add("rejects_invalid_dates", True, "date" in clarification, "date" in clarification)
        flags.append("needs_clarification")
    if run.status == "failed":
        flags.append("run_failed")
    return checks, flags


async def run_benchmark(
    db: AsyncSession, user: User, slugs: list[str] | None = None
) -> list[BenchmarkResultItem]:
    """Execute benchmark scenarios through the real graph (demo mode, no latency) and persist results.

    Runs are stored (marked `source: benchmark`) but do not create trips in the user's library.
    """
    await ensure_benchmark_cases(db)
    await db.commit()
    stmt = select(BenchmarkCase).order_by(BenchmarkCase.created_at, BenchmarkCase.slug)
    if slugs:
        stmt = stmt.where(BenchmarkCase.slug.in_(slugs))
    cases = list((await db.execute(stmt)).scalars())
    # Keep canonical scenario order
    order = {c["slug"]: i for i, c in enumerate(BENCHMARK_CASES)}
    cases.sort(key=lambda c: order.get(c.slug, 999))

    results: list[BenchmarkResultItem] = []
    token = demo_latency_override.set(0.0)
    try:
        for case in cases:
            payload = payload_from_prompt(case.prompt)
            payload.update({"persist_trip": False, "source": "benchmark", "benchmark_slug": case.slug})
            run = await create_run(db, user_id=user.id, payload=payload)
            await db.commit()
            run = await execute_run(db, run.id)
            checks, flags = evaluate_case(case, run)
            evaluation_id: str | None = None
            overall: float | None = None
            if run.status == "completed":
                ev = await evaluate_run_deterministic(db, user_id=user.id, run=run, trip=None)
                ev.label = f"Benchmark · {case.title}"
                ev.summary = (
                    f"Deterministic evaluation of benchmark case '{case.slug}'. "
                    "Scores computed from the stored plan; not a model judge."
                )
                evaluation_id, overall = ev.id, ev.overall_score
            await db.commit()
            results.append(
                BenchmarkResultItem(
                    slug=case.slug,
                    title=case.title,
                    run_id=run.id,
                    run_public_id=run.public_id,
                    run_status=run.status,
                    evaluation_id=evaluation_id,
                    overall_score=overall,
                    passed=bool(checks) and all(c["passed"] for c in checks),
                    checks=checks,
                    flags=sorted(set(flags)),
                )
            )
    finally:
        demo_latency_override.reset(token)
    return results
