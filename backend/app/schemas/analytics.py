from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from app.schemas.common import APIModel
from app.schemas.runs import RunOut
from app.schemas.trips import TripListItem


class DashboardOut(APIModel):
    greeting_name: str
    trips_planned: int
    trips_completed: int
    trips_in_progress: int
    trips_draft: int
    agent_runs: int
    avg_plan_quality: Optional[float] = None
    total_ai_cost_usd: float
    recent_trips: list[TripListItem] = Field(default_factory=list)
    agent_activity: list[dict[str, Any]] = Field(default_factory=list)
    provenance: str = "database"


class EvaluationMetricOut(APIModel):
    name: str
    value: Optional[float] = None
    unit: str = ""
    weight: float = 0.0
    provenance: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)


class EvaluationEvidenceOut(APIModel):
    metric_name: str
    snippet: str
    source_ref: str


class EvaluationOut(APIModel):
    id: str
    run_id: str
    run_public_id: Optional[str] = None
    kind: str
    label: str
    overall_score: Optional[float] = None
    status: str
    rubric_version: str
    is_demo_fixture: bool
    summary: str
    judge_model: Optional[str] = None
    judge_prompt_version: Optional[str] = None
    metrics: list[EvaluationMetricOut] = Field(default_factory=list)
    evidence: list[EvaluationEvidenceOut] = Field(default_factory=list)
    created_at: datetime
    run: Optional[RunOut] = None


class EvaluationCreateIn(APIModel):
    run_id: str
    kind: str = "deterministic"


class CompareIn(APIModel):
    run_ids: list[str] = Field(min_length=2, max_length=4)


class CompareRunOut(APIModel):
    run_id: str
    public_id: str
    status: str
    model_name: str
    ai_mode: str
    wall_time_ms: int
    total_cost_usd: float
    input_tokens: int
    output_tokens: int
    evaluations: list[EvaluationOut] = Field(default_factory=list)
    metrics: dict[str, Optional[float]] = Field(default_factory=dict)
    overall_by_kind: dict[str, Optional[float]] = Field(default_factory=dict)
    is_demo_fixture: bool = False


class CompareOut(APIModel):
    baseline_run_id: str
    runs: list[CompareRunOut]
    metric_names: list[str]
    metric_units: dict[str, str] = Field(default_factory=dict)
    metric_provenance: dict[str, str] = Field(default_factory=dict)
    # metric -> run_id -> delta vs baseline (None when either side is missing)
    deltas: dict[str, dict[str, Optional[float]]] = Field(default_factory=dict)
    missing: list[dict[str, str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class BenchmarkIn(APIModel):
    case_slugs: Optional[list[str]] = None


class BenchmarkCaseOut(APIModel):
    slug: str
    title: str
    prompt: str
    expected: dict[str, Any] = Field(default_factory=dict)
    tags: list[Any] = Field(default_factory=list)


class BenchmarkResultItem(APIModel):
    slug: str
    title: str
    run_id: Optional[str] = None
    run_public_id: Optional[str] = None
    run_status: str
    evaluation_id: Optional[str] = None
    overall_score: Optional[float] = None
    passed: bool
    checks: list[dict[str, Any]] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)


class BenchmarkOut(APIModel):
    total: int
    passed: int
    failed: int
    results: list[BenchmarkResultItem]
    provenance: str = "demo"


class CostSummaryOut(APIModel):
    total_cost_usd: float
    total_tokens: int
    input_tokens: int
    output_tokens: int
    avg_cost_per_run_usd: float
    by_agent: list[dict[str, Any]] = Field(default_factory=list)
    by_model: list[dict[str, Any]] = Field(default_factory=list)
    trend: list[dict[str, Any]] = Field(default_factory=list)
    provenance: str = "demo"
    currency: str = "USD"
    model_cost_usd: float = 0.0
    tool_cost_usd: float = 0.0
    run_count: int = 0
    unpriced_run_count: int = 0
    filters: dict[str, Any] = Field(default_factory=dict)
    note: str = "Seeded demo charges are illustrative, not an invoice."


class CostRunDetailOut(APIModel):
    run: RunOut
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    by_agent: list[dict[str, Any]] = Field(default_factory=list)
    by_model: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    waterfall: list[dict[str, Any]] = Field(default_factory=list)
    provenance: str = "demo"
    currency: str = "USD"
    reconciliation: dict[str, Any] = Field(default_factory=dict)
    wall_time_ms: int = 0
    note: str = (
        "Agent durations overlap (parallel fan-out); wall time is measured end to end and is "
        "not the sum of per-agent durations."
    )
