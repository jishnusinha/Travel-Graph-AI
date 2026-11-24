"""Idempotent, deterministic demo seed (local/demo mode only).

Everything seeded here is *illustrative demo data*: sample travel prices come from the local
catalog (not live inventory), AI costs are simulated, and every evaluation is labelled
"Sample evaluation (demo)". Itineraries are produced by running the REAL LangGraph workflow in
demo mode, so seeded plans match what a live demo run would generate.

Main scenario (consistent across every screen):
    Goa Getaway / "Goa Escape Plan" · Kolkata -> Goa · 12-16 Jan 2027 · 2 travelers · INR 35,000
    estimate INR 34,850 = 12,500 + 9,200 + 5,400 + 3,650 + 2,600 + 1,500
    run TG-1047: 14.2 s wall, 28,960 in + 7,460 out tokens, $0.237 = $0.217 model + $0.020 tool
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from unittest import mock

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password
from app.config import get_settings
from app.db.base import utcnow
from app.db.migrate import create_all
from app.db.session import SessionLocal
from app.graph.workflow import build_travel_graph
from app.models import (
    AgentEvent,
    AgentRun,
    BenchmarkCase,
    CostLineItem,
    EvaluationEvidence,
    EvaluationMetric,
    EvaluationRun,
    ModelInvocation,
    ModelPricingSnapshot,
    ToolInvocation,
    Trip,
    TripVersion,
    User,
    UserPreferences,
)
from app.providers.catalog import catalog_provider
from app.providers.llm import DemoLLMProvider, demo_latency_override
from app.services.accounting import (
    DEMO_INPUT_TOKENS,
    DEMO_MODEL_COST,
    DEMO_OUTPUT_TOKENS,
    DEMO_ROLE_COSTS,
    DEMO_ROLE_TOKENS,
    DEMO_ROLE_TOOL_COSTS,
    DEMO_TOOL_COST,
    DEMO_TOTAL_COST,
    DEMO_WALL_TIME_MS,
    role_model_cost,
    validate_demo_math,
)
from app.services.benchmark import ensure_benchmark_cases
from app.services.evaluation import compute_overall_score, evaluate_run_deterministic
from app.services.trip_service import apply_plan_to_trip, slugify

logger = logging.getLogger("travelgraph.seed")

DEMO_EMAIL = "demo@travelgraph.local"
REVIEWER_EMAIL = "reviewer@travelgraph.local"
DEMO_PASSWORD = "TravelGraphDemo!2026"
FIXTURE_LABEL = "Sample evaluation (demo)"

ROLES = ["supervisor", "destination", "transport", "accommodation", "itinerary", "aggregator"]
TOOL_NAMES = {
    "destination": "travel_catalog.attractions",
    "transport": "travel_catalog.transport",
    "accommodation": "travel_catalog.hotels",
}
INPUT_KEYS = {
    "supervisor": ["user_id", "trip_id", "thread_id", "run_id", "trip_request"],
    "destination": ["normalized_request", "constraints"],
    "transport": ["normalized_request", "constraints"],
    "accommodation": ["normalized_request", "constraints"],
    "itinerary": ["normalized_request", "research", "transport_options", "accommodation_options"],
    "validator": ["itinerary_days", "budget_breakdown", "normalized_request"],
    "aggregator": ["budget_breakdown", "itinerary_days", "validation_findings"],
}
STATE_KEYS = {
    "supervisor": ["needs_clarification", "normalized_request", "constraints", "messages", "event_meta"],
    "destination": ["research", "travel_advisories", "tool_results", "messages"],
    "transport": ["transport_options", "tool_results", "messages"],
    "accommodation": ["accommodation_options", "tool_results", "messages"],
    "itinerary": ["itinerary_days", "budget_breakdown", "messages"],
    "validator": ["validation_findings", "retry_count", "messages"],
    "aggregator": ["final_plan", "messages"],
}

# Node spans in ms: (start, end, (tool_start, tool_end) | None). Destination/transport/accommodation
# overlap (parallel fan-out), so summed node time (22.5 s) far exceeds the 14.2 s wall time.
PARALLEL_BASE_WALL = DEMO_WALL_TIME_MS
PARALLEL_SHAPE: dict[str, tuple[int, int, tuple[int, int] | None]] = {
    "supervisor": (120, 2150, None),
    "destination": (2200, 6900, (2800, 3150)),
    "transport": (2230, 6300, (2900, 3300)),
    "accommodation": (2260, 7000, (3000, 3400)),
    "itinerary": (7050, 11600, None),
    "validator": (11650, 12000, None),
    "aggregator": (12050, 14100, None),
}
# Older baseline configuration (TG-1039): same agents but run one after another
SEQUENTIAL_BASE_WALL = 31400
SEQUENTIAL_SHAPE: dict[str, tuple[int, int, tuple[int, int] | None]] = {
    "supervisor": (100, 2500, None),
    "destination": (2600, 8300, (3300, 3700)),
    "transport": (8400, 13200, (9000, 9400)),
    "accommodation": (13300, 19000, (13900, 14300)),
    "itinerary": (19100, 27000, None),
    "validator": (27100, 27600, None),
    "aggregator": (27700, 31300, None),
}

# TG-1039 (baseline comparison run): 25,310 in + 6,120 out tokens, $0.197 = $0.179 model + $0.018 tool
TG1039_TOKENS = {
    "supervisor": (2600, 650),
    "destination": (5000, 1100),
    "transport": (3900, 950),
    "accommodation": (4100, 1100),
    "itinerary": (6400, 1900),
    "aggregator": (3310, 420),
}
TG1039_COSTS = {
    "supervisor": 0.015,
    "destination": 0.036,
    "transport": 0.031,
    "accommodation": 0.034,
    "itinerary": 0.061,
    "aggregator": 0.020,
}
TG1039_TOOL_COSTS = {"destination": 0.007, "transport": 0.005, "accommodation": 0.006}

# Illustrative pricing catalog (NOT current provider prices; seeded run charges are simulated)
PRICING = [
    ("demo-local", 3.00, 12.00, 0.75),
    ("demo-fast", 0.60, 2.40, 0.15),
    ("demo-reasoning", 8.00, 32.00, 2.00),
]

# Historical "Sample evaluation (demo)" judge scores: (relevance, coherence, feasibility, recommendation)
JUDGE_FIXTURES: dict[str, tuple[float, float, float, float]] = {
    "TG-1047": (4.6, 4.5, 4.3, 4.4),
    "TG-1039": (4.1, 4.0, 3.8, 3.9),
    "TG-1036": (4.4, 4.2, 4.0, 4.1),
    "TG-1033": (4.3, 4.3, 4.1, 4.0),
    "TG-1029": (4.2, 4.1, 3.9, 4.0),
    "TG-1026": (4.5, 4.4, 4.2, 4.3),
    "TG-1020": (4.3, 4.2, 4.2, 4.1),
    "TG-1014": (4.0, 4.1, 4.0, 3.9),
    "TG-2001": (4.2, 4.1, 4.0, 4.0),
}
JUDGE_WEIGHTS = {"relevance": 0.30, "coherence": 0.25, "feasibility": 0.25, "recommendation_quality": 0.20}

GOA_PROMPT = (
    "Plan a 5-day Goa trip from Kolkata for 2 travelers from 2027-01-12 to 2027-01-16 under ₹35,000 total. "
    "We love beaches, local Goan food and relaxed sightseeing."
)


# ============================================================================ specs
@dataclass
class RunSpec:
    public_id: str
    days_ago: float
    hour: int
    trip_key: str | None = None
    model: str = "demo-local"
    status: str = "completed"  # completed | failed | needs_clarification
    tok_mult: float = 1.0
    cost_mult: float = 1.0
    wall_ms: int = PARALLEL_BASE_WALL
    shape: str = "parallel"
    canonical: bool = False
    tokens: dict[str, tuple[int, int]] | None = None
    costs: dict[str, float] | None = None
    tool_costs: dict[str, float] | None = None
    plan_variant: str | None = None
    revision: int = 1
    minute: int = 12
    # fillers without a saved trip
    dest: str | None = None
    days: int = 4
    prompt: str | None = None
    error: str | None = None
    failed_node: str | None = None
    notes: dict[str, Any] = field(default_factory=dict)


def _trip(key, title, dest, status, *, start=None, end=None, travelers=2, budget=35000, interests=None,
          favorite=False, created_days_ago=20.0, updated_days_ago=None, prompt=None):
    return {
        "key": key, "title": title, "destination": dest, "status": status, "start": start, "end": end,
        "travelers": travelers, "budget": budget, "interests": interests or [], "favorite": favorite,
        "created_days_ago": created_days_ago, "updated_days_ago": updated_days_ago, "prompt": prompt,
    }


DEMO_TRIPS = [
    # --- 7 completed
    _trip("goa", "Goa Getaway", "Goa", "completed", start="2027-01-12", end="2027-01-16", travelers=2, budget=35000,
          interests=["beaches", "local Goan food", "relaxed sightseeing"], favorite=True, prompt=GOA_PROMPT),
    _trip("jaipur", "Jaipur Heritage Weekend", "Jaipur", "completed", start="2026-12-05", end="2026-12-07",
          budget=30000, interests=["heritage", "forts", "street food"]),
    _trip("udaipur", "Udaipur Lakeside Escape", "Udaipur", "completed", start="2026-12-18", end="2026-12-21",
          budget=38000, interests=["lakes", "palaces", "romantic evenings"], favorite=True),
    _trip("munnar", "Munnar Tea Trails", "Munnar", "completed", start="2027-02-06", end="2027-02-09",
          budget=38000, interests=["tea estates", "nature", "slow travel"]),
    _trip("kerala", "Kerala Backwaters Retreat", "Kerala", "completed", start="2027-02-20", end="2027-02-24",
          budget=50000, interests=["backwaters", "houseboat", "ayurveda"], favorite=True),
    _trip("manali", "Manali Family Mountain Break", "Manali", "completed", start="2026-12-26", end="2026-12-31",
          travelers=4, budget=40000, interests=["mountains", "family", "snow"]),
    _trip("darjeeling", "Darjeeling Himalayan Escape", "Darjeeling", "completed", start="2026-11-27", end="2026-11-30",
          budget=28000, interests=["tea", "toy train", "sunrise views"]),
    # --- 2 in progress (partial itinerary still being refined)
    _trip("rishikesh", "Rishikesh Yoga & Rafting", "Rishikesh", "in_progress", start="2027-03-06", end="2027-03-09",
          budget=36000, interests=["yoga", "rafting", "ganga aarti"], updated_days_ago=1.2),
    _trip("manali_winter", "Manali Winter Snow Trip", "Manali", "in_progress", start="2027-01-25", end="2027-01-29",
          budget=36000, interests=["snow", "cafes", "mountains"], updated_days_ago=0.6),
    # --- 3 drafts
    _trip("jaipur_solo", "Jaipur Solo City Break", "Jaipur", "draft", start="2027-03-05", end="2027-03-07",
          travelers=1, budget=20000, interests=["museums", "cafes"], favorite=True, created_days_ago=5.0,
          updated_days_ago=0.4, prompt="3-day Jaipur solo city break under ₹20,000."),
    _trip("udaipur_anniv", "Udaipur Anniversary Weekend", "Udaipur", "draft", travelers=2, budget=45000,
          interests=["romantic", "fine dining"], created_days_ago=8.0, updated_days_ago=3.0,
          prompt="Plan a romantic anniversary weekend in Udaipur for two."),
    _trip("goa_workation", "Goa Monsoon Workation", "Goa", "draft", start="2027-07-10", end="2027-07-14", travelers=1,
          budget=30000, interests=["cafes", "quiet beaches"], created_days_ago=12.0, updated_days_ago=2.0,
          prompt="Plan a 5-day monsoon workation in Goa with good wifi and quiet beaches."),
]

DEMO_RUNS: list[RunSpec] = [
    RunSpec("TG-1012", 36, 9, dest="Jaipur", days=3, tok_mult=0.92, cost_mult=0.92, wall_ms=13500),
    RunSpec("TG-1014", 34, 14, "darjeeling", tok_mult=0.95, cost_mult=0.95, wall_ms=13100, minute=21),
    RunSpec("TG-1016", 32, 11, model="demo-fast", dest="Manali", days=4, tok_mult=0.9, cost_mult=0.6, wall_ms=9800),
    RunSpec("TG-1018", 30, 16, model="demo-reasoning", dest="Udaipur", days=4, tok_mult=1.3, cost_mult=1.6, wall_ms=19400),
    RunSpec("TG-1020", 28, 10, "jaipur", tok_mult=0.9, cost_mult=0.9, wall_ms=12600, minute=34),
    RunSpec("TG-1022", 26, 12, model="demo-fast", dest="Munnar", days=4, tok_mult=0.88, cost_mult=0.58, wall_ms=9400),
    RunSpec("TG-1024", 25, 18, status="failed", dest="Goa", days=5, wall_ms=9100, failed_node="itinerary",
            prompt="Plan a 5-day Goa luxury trip for 2 under ₹8,000.",
            error="Demo fixture: itinerary retry limit reached after 3 attempts (budget conflict)."),
    RunSpec("TG-1026", 23, 9, "udaipur", tok_mult=1.05, cost_mult=1.05, wall_ms=14600, minute=48),
    RunSpec("TG-1027", 22, 15, model="demo-reasoning", dest="Kerala", days=5, tok_mult=1.28, cost_mult=1.55, wall_ms=20100),
    RunSpec("TG-1029", 20, 11, "manali", tok_mult=1.1, cost_mult=1.1, wall_ms=15300, minute=5),
    RunSpec("TG-1030", 19, 17, model="demo-fast", dest="Darjeeling", days=4, tok_mult=0.9, cost_mult=0.6, wall_ms=9700),
    RunSpec("TG-1031", 17, 10, status="needs_clarification", wall_ms=2000,
            prompt="Plan a relaxing 5-day trip for two under ₹35,000.",
            error="Missing required fields: destination"),
    RunSpec("TG-1033", 16, 13, "munnar", tok_mult=0.97, cost_mult=0.97, wall_ms=13400, minute=27),
    RunSpec("TG-1034", 14, 9, dest="Goa", days=5, tok_mult=1.02, cost_mult=1.02, wall_ms=14500),
    RunSpec("TG-1036", 13, 16, "kerala", model="demo-reasoning", tok_mult=1.32, cost_mult=1.62, wall_ms=19800, minute=40),
    RunSpec("TG-1037", 11, 12, model="demo-fast", dest="Jaipur", days=3, tok_mult=0.86, cost_mult=0.57, wall_ms=9100),
    RunSpec("TG-1038", 10, 15, "rishikesh", tok_mult=0.93, cost_mult=0.93, wall_ms=13000, minute=16),
    RunSpec("TG-1039", 9, 10, "goa", model="demo-fast", shape="sequential", wall_ms=SEQUENTIAL_BASE_WALL,
            tokens=TG1039_TOKENS, costs=TG1039_COSTS, tool_costs=TG1039_TOOL_COSTS, plan_variant="baseline",
            minute=2),
    RunSpec("TG-1041", 8, 14, dest="Udaipur", days=4, tok_mult=1.0, cost_mult=1.0, wall_ms=14100),
    RunSpec("TG-1042", 7, 11, "jaipur", tok_mult=0.89, cost_mult=0.89, wall_ms=12400, revision=2, minute=9),
    RunSpec("TG-1043", 6, 9, "manali_winter", tok_mult=1.0, cost_mult=1.0, wall_ms=14800, minute=31),
    RunSpec("TG-1044", 5, 13, model="demo-reasoning", dest="Munnar", days=4, tok_mult=1.25, cost_mult=1.5, wall_ms=18900),
    RunSpec("TG-1045", 4, 15, "udaipur", model="demo-fast", tok_mult=0.9, cost_mult=0.6, wall_ms=9900, revision=2, minute=44),
    RunSpec("TG-1046", 3, 10, dest="Darjeeling", days=4, tok_mult=0.96, cost_mult=0.96, wall_ms=13300),
    RunSpec("TG-1047", 2, 11, "goa", canonical=True, minute=8),
]

REVIEWER_TRIPS = [
    _trip("darjeeling", "Darjeeling Tea Weekend", "Darjeeling", "completed", start="2027-03-12", end="2027-03-15",
          budget=25000, interests=["tea", "mountains", "culture"], favorite=True),
    _trip("rishikesh", "Rishikesh Reset", "Rishikesh", "completed", start="2026-12-10", end="2026-12-13",
          travelers=1, budget=36000, interests=["wellness", "yoga"]),
    _trip("jaipur_food", "Jaipur Food Trail", "Jaipur", "in_progress", start="2027-01-20", end="2027-01-22",
          budget=30000, interests=["street food", "markets"], updated_days_ago=1.0),
    _trip("kerala_draft", "Kerala Backwaters Draft", "Kerala", "draft", travelers=2, budget=48000,
          interests=["backwaters"], created_days_ago=6.0, updated_days_ago=2.5,
          prompt="Plan a calm Kerala backwaters getaway for two."),
]

REVIEWER_RUNS = [
    RunSpec("TG-2001", 12, 10, "darjeeling", tok_mult=0.94, cost_mult=0.94, wall_ms=13200, minute=15),
    RunSpec("TG-2002", 8, 14, "rishikesh", model="demo-fast", tok_mult=0.9, cost_mult=0.6, wall_ms=9900, minute=37),
    RunSpec("TG-2003", 3, 12, "jaipur_food", tok_mult=0.9, cost_mult=0.9, wall_ms=12100, minute=22),
]


# ============================================================================ helpers
async def build_plan(payload: dict[str, Any]) -> dict[str, Any]:
    """Run the real LangGraph workflow in demo mode (forced demo LLM, no simulated latency)."""
    graph = build_travel_graph()
    initial = {
        "trip_request": payload,
        "messages": [],
        "agent_errors": [],
        "tool_results": {},
        "retry_count": 0,
        "revision_number": 1,
    }
    token = demo_latency_override.set(0.0)
    try:
        # Never let a configured AI_MODE=openai leak into seeding
        with mock.patch("app.graph.nodes.get_llm_provider", lambda: DemoLLMProvider()):
            state = await graph.ainvoke(initial)
    finally:
        demo_latency_override.reset(token)
    plan = state.get("final_plan") or {}
    if not plan:
        raise RuntimeError(f"Seed plan generation produced no plan for {payload.get('destination')}")
    return plan


def _baseline_goa_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """TG-1039: earlier config, stay priced 9,600 -> total 35,250 (INR 250 over budget, flagged)."""
    base = copy.deepcopy(plan)
    bb = base["budget_breakdown"]
    bb["accommodation"] = 9600
    bb["total"] = sum(bb[k] for k in ("intercity_travel", "accommodation", "meals", "local_travel", "attractions", "contingency"))
    bb["remaining"] = base["budget_inr"] - bb["total"]
    base["estimated_cost_inr"] = bb["total"]
    base["accommodation"] = {**base["accommodation"], "nightly_inr": 2400, "total_inr": 9600}
    base["validation_findings"] = [
        {
            "code": "budget_over_limit",
            "severity": "warning",
            "message": f"Estimated ₹{bb['total']} exceeds budget ₹{base['budget_inr']} by ₹{-bb['remaining']}",
            "correctable": False,
        }
    ]
    base["recommendation"] = "Estimated costs exceed the stated budget — consider adjusting dates or lodging."
    return base


def _payload_for(spec: dict[str, Any]) -> dict[str, Any]:
    days = None
    if spec["start"] and spec["end"]:
        days = (date.fromisoformat(spec["end"]) - date.fromisoformat(spec["start"])).days + 1
    prompt = spec["prompt"] or (
        f"Plan a {days or 4}-day {spec['destination']} trip from Kolkata for {spec['travelers']} "
        f"under ₹{spec['budget']:,}. Interests: {', '.join(spec['interests']) or 'sightseeing'}."
    )
    return {
        "prompt": prompt,
        "destination": spec["destination"],
        "origin": "Kolkata, India",
        "start_date": spec["start"],
        "end_date": spec["end"],
        "travelers": spec["travelers"],
        "budget_inr": spec["budget"],
        "interests": list(spec["interests"]),
    }


def _scaled_shape(spec: RunSpec) -> dict[str, tuple[int, int, tuple[int, int] | None]]:
    base_shape, base_wall = (
        (SEQUENTIAL_SHAPE, SEQUENTIAL_BASE_WALL) if spec.shape == "sequential" else (PARALLEL_SHAPE, PARALLEL_BASE_WALL)
    )
    f = spec.wall_ms / base_wall if spec.status == "completed" else 1.0
    out = {}
    for node, (s, e, tool) in base_shape.items():
        out[node] = (
            int(round(s * f)),
            int(round(e * f)),
            (int(round(tool[0] * f)), int(round(tool[1] * f))) if tool else None,
        )
    return out


def _role_data(spec: RunSpec) -> dict[str, dict[str, Any]]:
    tokens = spec.tokens or DEMO_ROLE_TOKENS
    costs = spec.costs or DEMO_ROLE_COSTS
    tools = spec.tool_costs or DEMO_ROLE_TOOL_COSTS
    out = {}
    for role in ROLES:
        tin, tout = tokens[role]
        if spec.canonical or (spec.tok_mult == 1.0 and spec.cost_mult == 1.0):
            m_cost = role_model_cost(role, costs, tools)
            t_cost = float(tools.get(role, 0.0))
        else:
            m_cost = round(role_model_cost(role, costs, tools) * spec.cost_mult, 6)
            t_cost = round(float(tools.get(role, 0.0)) * spec.cost_mult, 6)
        out[role] = {
            "tin": int(round(tin * spec.tok_mult)),
            "tout": int(round(tout * spec.tok_mult)),
            "model_cost": m_cost,
            "tool_cost": t_cost,
        }
    return out


def _summaries(plan: dict[str, Any], payload: dict[str, Any]) -> dict[str, str]:
    dest = catalog_provider.lookup_destination(plan.get("destination") or payload.get("destination") or "")
    budget = int(plan.get("budget_inr") or payload.get("budget_inr") or 35000)
    hotels = dest.get("hotels") or []
    stays = [h for h in hotels if h.get("total_inr", 0) <= budget * 0.4] or hotels
    days = plan.get("days") or []
    return {
        "supervisor": f"Parsed {plan.get('destination')} · {len(days)} days",
        "destination": f"Research: {len(dest.get('attractions') or [])} attractions",
        "transport": f"{len(dest.get('transport') or [])} transport options",
        "accommodation": f"{len(stays)} stays compared",
        "itinerary": f"{len(days)} days scheduled",
        "validator": f"{len(plan.get('validation_findings') or [])} findings",
        "aggregator": "Final plan compiled",
    }


def _build_event_rows(
    spec: RunSpec,
    shape: dict[str, tuple[int, int, tuple[int, int] | None]],
    roles: dict[str, dict[str, Any]],
    plan: dict[str, Any],
    payload: dict[str, Any],
    public_id: str,
) -> tuple[list[tuple[int, str, str | None, str | None, dict[str, Any]]], int]:
    """Return ([(offset_ms, type, node, status, payload)], terminal_offset_ms) sorted by time."""
    summaries = _summaries(plan, payload)
    order = ["supervisor", "destination", "transport", "accommodation", "itinerary", "validator", "aggregator"]
    if spec.status == "needs_clarification":
        run_nodes = ["supervisor"]
    elif spec.status == "failed" and spec.failed_node:
        run_nodes = order[: order.index(spec.failed_node) + 1]
    else:
        run_nodes = order

    rows: list[tuple[int, str, str | None, str | None, dict[str, Any]]] = []
    rows.append((0, "run.created", None, "pending", {"public_id": public_id}))
    rows.append((40, "run.started", None, "running", {}))
    last_end = 0
    for node in run_nodes:
        start, end, tool = shape[node]
        failed = spec.status == "failed" and node == spec.failed_node
        if spec.status == "needs_clarification":
            end = max(end - 250, start + 400)
        if failed:
            end = start + 1900  # fails after bounded retries
        last_end = max(last_end, end)
        rows.append((start, "agent.started", node, "running", {"input_keys": INPUT_KEYS[node], "attempt": 1}))
        if tool and not failed:
            rows.append((tool[0], "tool.called", node, "running", {"tool": TOOL_NAMES[node]}))
            rows.append(
                (tool[1], "tool.succeeded", node, "succeeded",
                 {"tool": TOOL_NAMES[node], "fee_usd": roles[node]["tool_cost"]})
            )
        data = roles.get(node)
        if data and not failed:
            rows.append(
                (start + int((end - start) * 0.45), "agent.progress", node, "running",
                 {"stage": "llm_call", "model": spec.model, "tokens_in": data["tin"], "tokens_out": data["tout"]})
            )
        if failed:
            rows.append(
                (end, "agent.failed", node, "failed",
                 {"error": spec.error or "Run failed", "duration_ms": end - start, "attempt": 3})
            )
            continue
        if node == "validator":
            for f in plan.get("validation_findings") or []:
                if f.get("severity") == "warning":
                    rows.append((end - 6, "validation.warning", node, "warning", f))
        keys = STATE_KEYS[node]
        if spec.status == "needs_clarification":
            keys = ["needs_clarification", "clarification_prompt", "normalized_request", "messages"]
        rows.append((end - 3, "state.updated", node, "running", {"keys": keys}))
        completed_payload: dict[str, Any] = {
            "duration_ms": end - start,
            "summary": "Clarification needed" if spec.status == "needs_clarification" else summaries[node],
            "attempt": 1,
        }
        if data:
            completed_payload.update(
                {
                    "model": spec.model,
                    "tokens_in": data["tin"],
                    "tokens_out": data["tout"],
                    "cost_usd": round(data["model_cost"] + data["tool_cost"], 6),
                }
            )
        rows.append((end, "agent.completed", node, "completed", completed_payload))

    if spec.status == "completed":
        terminal = spec.wall_ms
        rows.append((terminal, "run.completed", None, "completed", {"wall_time_ms": terminal}))
    elif spec.status == "failed":
        terminal = last_end + 100
        rows.append((terminal, "run.failed", None, "failed", {"error": spec.error}))
    else:
        terminal = last_end + 100
        rows.append(
            (terminal, "run.needs_clarification", None, "needs_clarification",
             {"wall_time_ms": terminal, "clarification": spec.error})
        )
    rows.sort(key=lambda r: r[0])  # stable: ties keep emission order
    return rows, terminal


async def _persist_run(
    db: AsyncSession,
    *,
    user: User,
    spec: RunSpec,
    trip: Trip | None,
    plan: dict[str, Any],
    payload: dict[str, Any],
    now: datetime,
    pricing_ids: dict[str, str],
) -> AgentRun:
    started = (now - timedelta(days=spec.days_ago)).replace(
        hour=spec.hour, minute=spec.minute, second=7, microsecond=0
    )
    shape = _scaled_shape(spec)
    roles = _role_data(spec)
    rows, terminal_ms = _build_event_rows(spec, shape, roles, plan, payload, spec.public_id)
    wall_ms = terminal_ms
    completed_at = started + timedelta(milliseconds=wall_ms)

    if spec.status == "needs_clarification":
        executed = ["supervisor"]
    elif spec.status == "failed" and spec.failed_node:
        executed = ROLES[: ROLES.index(spec.failed_node)]  # failed node produced no billable output
    else:
        executed = list(ROLES)

    tin = sum(roles[r]["tin"] for r in executed)
    tout = sum(roles[r]["tout"] for r in executed)
    model_cost = round(sum(roles[r]["model_cost"] for r in executed), 6)
    tool_cost = round(sum(roles[r]["tool_cost"] for r in executed), 6)
    total_cost = round(model_cost + tool_cost, 6)
    if spec.canonical:  # TG-1047: exact documented example totals
        tin, tout = DEMO_INPUT_TOKENS, DEMO_OUTPUT_TOKENS
        model_cost, tool_cost, total_cost = DEMO_MODEL_COST, DEMO_TOOL_COST, DEMO_TOTAL_COST

    run = AgentRun(
        public_id=spec.public_id,
        user_id=user.id,
        trip_id=trip.id if trip else None,
        thread_id=f"thread-seed-{spec.public_id.lower()}",
        status=spec.status,
        prompt=payload.get("prompt", ""),
        request_payload={**payload, "source": "seed"},
        final_plan=plan if spec.status == "completed" else {},
        ai_mode="demo",
        model_name=spec.model,
        started_at=started,
        completed_at=completed_at,
        wall_time_ms=wall_ms,
        input_tokens=tin,
        output_tokens=tout,
        model_cost_usd=model_cost,
        tool_cost_usd=tool_cost,
        total_cost_usd=total_cost,
        cost_provenance="demo",
        error_message=spec.error if spec.status != "completed" else None,
        revision_number=spec.revision,
        created_at=started - timedelta(seconds=1),
        updated_at=completed_at,
    )
    db.add(run)
    await db.flush()

    for seq, (offset, etype, node, status, body) in enumerate(rows, start=1):
        ts = started + timedelta(milliseconds=offset)
        db.add(
            AgentEvent(
                run_id=run.id, seq=seq, ts=ts, type=etype, node_id=node, status=status,
                payload=body, created_at=ts, updated_at=ts,
            )
        )

    for role in executed:
        start, end, tool = shape[role]
        if spec.status == "needs_clarification":
            end = max(end - 250, start + 400)
        data = roles[role]
        occurred = started + timedelta(milliseconds=end)
        db.add(
            ModelInvocation(
                run_id=run.id, node_id=role, provider="demo", model=spec.model,
                input_tokens=data["tin"], output_tokens=data["tout"], cached_tokens=0,
                pricing_snapshot_id=pricing_ids.get(spec.model),
                estimated_cost_usd=data["model_cost"], cost_status="demo",
                duration_ms=int((end - start) * 0.62), created_at=occurred, updated_at=occurred,
            )
        )
        db.add(
            CostLineItem(
                run_id=run.id, user_id=user.id, category="model", agent_role=role, model=spec.model,
                amount_usd=data["model_cost"], tokens_in=data["tin"], tokens_out=data["tout"],
                provenance="demo", occurred_at=occurred, created_at=occurred, updated_at=occurred,
            )
        )
        if role in TOOL_NAMES and tool and data["tool_cost"] > 0:
            tool_end = started + timedelta(milliseconds=tool[1])
            db.add(
                ToolInvocation(
                    run_id=run.id, node_id=role, tool_name=TOOL_NAMES[role], status="succeeded",
                    duration_ms=tool[1] - tool[0], fee_usd=data["tool_cost"], provenance="local-catalog",
                    input_summary={"destination": payload.get("destination")},
                    output_summary={"ok": True, "source": "local-catalog-sample"},
                    created_at=tool_end, updated_at=tool_end,
                )
            )
            db.add(
                CostLineItem(
                    run_id=run.id, user_id=user.id, category="tool", agent_role=role,
                    tool_name=TOOL_NAMES[role], amount_usd=data["tool_cost"], provenance="demo",
                    occurred_at=tool_end, created_at=tool_end, updated_at=tool_end,
                )
            )
    await db.flush()
    return run


async def _add_evaluations(
    db: AsyncSession, *, user: User, run: AgentRun, trip: Trip | None, spec: RunSpec
) -> int:
    """Deterministic evaluation computed from the stored plan + judge-style sample scores."""
    created = 0
    stamp = (run.completed_at or utcnow()) + timedelta(minutes=2)
    ev = await evaluate_run_deterministic(db, user_id=user.id, run=run, trip=trip)
    ev.label = FIXTURE_LABEL
    ev.is_demo_fixture = True
    ev.summary = (
        f"{FIXTURE_LABEL}: deterministic rubric scores computed from the stored plan for {run.public_id}. "
        "Seeded as a historical fixture; not a model judge."
    )
    ev.created_at = ev.updated_at = stamp
    created += 1

    scores = JUDGE_FIXTURES.get(run.public_id)
    if scores:
        names = ["relevance", "coherence", "feasibility", "recommendation_quality"]
        overall = compute_overall_score([(n, v, "/5", JUDGE_WEIGHTS[n]) for n, v in zip(names, scores)])
        judge = EvaluationRun(
            user_id=user.id, run_id=run.id, kind="judge", label=FIXTURE_LABEL, overall_score=overall,
            status="completed", rubric_version="travelplan-judge-v1", is_demo_fixture=True,
            summary=f"{FIXTURE_LABEL}: fixed historical judge-style scores for {run.public_id}. "
            "No model was called; do not treat as an objective measurement.",
            judge_model="demo-judge-fixture", judge_prompt_version="judge-prompt-v1 (demo)",
            created_at=stamp, updated_at=stamp,
        )
        db.add(judge)
        await db.flush()
        for n, v in zip(names, scores):
            db.add(
                EvaluationMetric(
                    evaluation_id=judge.id, name=n, value=v, unit="/5", weight=JUDGE_WEIGHTS[n],
                    provenance="demo-fixture-judge", status="ok",
                    details={"uncertainty": 0.3, "fixture": True}, created_at=stamp, updated_at=stamp,
                )
            )
        db.add(
            EvaluationMetric(
                evaluation_id=judge.id, name="unsupported_claims", value=0.0, unit="count", weight=0.0,
                provenance="demo-fixture-judge", status="ok",
                details={"note": "Informational; excluded from overall (weight 0)", "fixture": True},
                created_at=stamp, updated_at=stamp,
            )
        )
        db.add(
            EvaluationEvidence(
                evaluation_id=judge.id, metric_name="feasibility",
                snippet="Daily schedule keeps transfers short and stays within the catalog price estimates.",
                source_ref=f"run:{run.public_id}", created_at=stamp, updated_at=stamp,
            )
        )
        created += 1
    await db.flush()
    return created


async def _seed_user_data(
    db: AsyncSession,
    user: User,
    trip_specs: list[dict[str, Any]],
    run_specs: list[RunSpec],
    pricing_ids: dict[str, str],
    now: datetime,
) -> dict[str, int]:
    trips: dict[str, Trip] = {}
    payloads: dict[str, dict[str, Any]] = {}
    plans: dict[str, dict[str, Any]] = {}
    for spec in trip_specs:
        payload = _payload_for(spec)
        payloads[spec["key"]] = payload
        if spec["status"] in {"completed", "in_progress"}:
            plan = await build_plan(payload)
            if spec["status"] == "in_progress":  # partial itinerary: first two days only
                plan = {**plan, "days": plan["days"][:2]}
            plans[spec["key"]] = plan
        cover = catalog_provider.lookup_destination(spec["destination"]).get("cover") or "/assets/destinations/generic.jpg"
        trip = Trip(
            user_id=user.id,
            title=spec["title"],
            slug=slugify(spec["title"]),
            destination=spec["destination"],
            origin="Kolkata, India",
            start_date=date.fromisoformat(spec["start"]) if spec["start"] else None,
            end_date=date.fromisoformat(spec["end"]) if spec["end"] else None,
            travelers=spec["travelers"],
            budget_inr=spec["budget"],
            estimated_cost_inr=0,
            status="draft",
            is_favorite=spec["favorite"],
            prompt=payload["prompt"],
            interests=list(spec["interests"]),
            cover_image=cover,
            current_version=1,
        )
        db.add(trip)
        await db.flush()
        trips[spec["key"]] = trip

    # Runs in chronological order so trip versions line up with run history
    run_times: dict[str, list[datetime]] = {k: [] for k in trips}
    counts = {"runs": 0, "events": 0, "evaluations": 0}
    filler_cache: dict[tuple, dict[str, Any]] = {}
    spec_by_key = {s["key"]: s for s in trip_specs}
    for rs in sorted(run_specs, key=lambda r: -r.days_ago):
        trip = trips.get(rs.trip_key) if rs.trip_key else None
        if trip is not None:
            payload = payloads[rs.trip_key]
            plan = plans[rs.trip_key]
            if rs.plan_variant == "baseline":
                plan = _baseline_goa_plan(plan)
        else:
            if rs.status == "needs_clarification":
                payload = {"prompt": rs.prompt, "travelers": 2, "budget_inr": 35000, "origin": "Kolkata, India"}
                plan = {}
            elif rs.status == "failed":
                payload = {"prompt": rs.prompt, "destination": rs.dest, "travelers": 2, "budget_inr": 8000,
                           "origin": "Kolkata, India", "interests": ["luxury"]}
                plan = {}
            else:
                start = date(2027, 1, 12) + timedelta(days=int(rs.days_ago))
                payload = {
                    "prompt": f"Plan a {rs.days}-day {rs.dest} trip from Kolkata for 2 under ₹60,000.",
                    "destination": rs.dest, "origin": "Kolkata, India", "travelers": 2, "budget_inr": 60000,
                    "start_date": start.isoformat(),
                    "end_date": (start + timedelta(days=rs.days - 1)).isoformat(),
                    "interests": ["sightseeing", "food"],
                }
                key = (rs.dest, rs.days)
                if key not in filler_cache:
                    filler_cache[key] = await build_plan(payload)
                plan = filler_cache[key]
        run = await _persist_run(
            db, user=user, spec=rs, trip=trip, plan=plan, payload=payload, now=now, pricing_ids=pricing_ids
        )
        counts["runs"] += 1
        if trip is not None and rs.status == "completed":
            tspec = spec_by_key[rs.trip_key]
            summary = (
                f"Generated by TravelGraph agents · {rs.public_id}"
                if rs.revision <= 1
                else f"Replanned by TravelGraph agents (revision {rs.revision}) · {rs.public_id}"
            )
            if tspec["status"] == "in_progress":
                summary = f"Partial itinerary saved · {rs.public_id}"
            await apply_plan_to_trip(
                db, trip, plan, prompt=payload["prompt"], change_summary=summary,
                status="completed" if tspec["status"] == "completed" else "in_progress",
            )
            version = (
                await db.execute(
                    select(TripVersion).where(TripVersion.trip_id == trip.id, TripVersion.version == trip.current_version)
                )
            ).scalar_one()
            version.created_at = version.updated_at = run.completed_at
            run_times[rs.trip_key].append(run.completed_at)
            if tspec["status"] == "completed":
                counts["evaluations"] += await _add_evaluations(db, user=user, run=run, trip=trip, spec=rs)
        ev_count = (
            await db.execute(select(AgentEvent.seq).where(AgentEvent.run_id == run.id))
        ).scalars().all()
        counts["events"] += len(ev_count)

    # Final trip timestamps (set last so no later UPDATE rewrites them)
    for spec in trip_specs:
        trip = trips[spec["key"]]
        times = sorted(run_times[spec["key"]])
        if times:
            created = times[0] - timedelta(minutes=2)
            updated = times[-1] + timedelta(minutes=5)
            if spec["updated_days_ago"] is not None:
                updated = now - timedelta(days=spec["updated_days_ago"])
        else:
            created = now - timedelta(days=spec["created_days_ago"])
            updated = now - timedelta(days=spec["updated_days_ago"] if spec["updated_days_ago"] is not None else spec["created_days_ago"])
        trip.created_at, trip.updated_at = created, max(updated, created)
    await db.flush()
    counts["trips"] = len(trips)
    return counts


async def _ensure_pricing(db: AsyncSession) -> dict[str, str]:
    existing = {p.model: p for p in (await db.execute(select(ModelPricingSnapshot))).scalars()}
    for model, inp, out, cached in PRICING:
        if model not in existing:
            row = ModelPricingSnapshot(
                model=model, provider="demo", input_per_1m_usd=inp, output_per_1m_usd=out,
                cached_per_1m_usd=cached, source_date="2026-01-01",
                notes="Demo pricing catalog — illustrative only. Seeded run charges are simulated and "
                "not derived from these rates; not a provider invoice.",
            )
            db.add(row)
            existing[model] = row
    await db.flush()
    return {m: p.id for m, p in existing.items()}


async def _delete_user(db: AsyncSession, email: str) -> bool:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    if user is None:
        return False
    await db.delete(user)  # ORM cascades: sessions, prefs, trips(+days/activities/versions), runs(+events/costs/evals)
    await db.flush()
    return True


# ============================================================================ public API
async def seed_demo(db: AsyncSession, reset: bool = False) -> dict[str, Any]:
    """Create demo data. Safe to call repeatedly: existing demo users are left untouched.

    ``reset=True`` first deletes the two seeded users (and everything they own), then reseeds.
    """
    validate_demo_math()
    summary: dict[str, Any] = {"reset": reset, "users": {}}
    now = utcnow()

    if reset:
        for email in (DEMO_EMAIL, REVIEWER_EMAIL):
            await _delete_user(db, email)
        for model in (ModelPricingSnapshot, BenchmarkCase):
            for row in (await db.execute(select(model))).scalars():
                await db.delete(row)
        await db.commit()

    pricing_ids = await _ensure_pricing(db)
    summary["benchmark_cases_added"] = await ensure_benchmark_cases(db)
    await db.commit()

    users = [
        (DEMO_EMAIL, "Alex Kumar", "AK", "+91 98300 00001", DEMO_TRIPS, DEMO_RUNS, {
            "interests": ["beaches", "local food", "relaxed sightseeing"], "budget_min": 20000, "budget_max": 50000,
            "accommodation_style": "mid-range", "transport_preference": "flights"}),
        (REVIEWER_EMAIL, "Riya Sen", "RS", "+91 98300 00002", REVIEWER_TRIPS, REVIEWER_RUNS, {
            "interests": ["culture", "mountains", "wellness"], "budget_min": 15000, "budget_max": 40000,
            "accommodation_style": "boutique", "transport_preference": "trains"}),
    ]
    for email, name, initials, phone, trip_specs, run_specs, prefs in users:
        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is not None:
            summary["users"][email] = {"status": "exists (skipped)"}
            continue
        try:
            user = User(
                email=email, full_name=name, password_hash=hash_password(DEMO_PASSWORD), phone=phone,
                timezone="Asia/Kolkata", is_demo=True, onboarding_completed=True, avatar_initials=initials,
                is_active=True, created_at=now - timedelta(days=40), updated_at=now - timedelta(days=40),
                preferences=UserPreferences(
                    home_city="Kolkata, India", currency="INR", ai_mode_preference="demo", theme="system",
                    reduced_motion=False, extra={"seeded": True}, **prefs,
                ),
            )
            db.add(user)
            await db.flush()
            counts = await _seed_user_data(db, user, trip_specs, run_specs, pricing_ids, now)
            await db.commit()
            summary["users"][email] = {"status": "created", **counts}
        except Exception:
            await db.rollback()
            raise
    return summary


async def run_seed(reset: bool = False) -> dict[str, Any]:
    """CLI entry: ensure schema, then seed (refuses to run in production)."""
    settings = get_settings()
    if settings.app_env == "production":
        raise RuntimeError("Refusing to seed demo accounts when APP_ENV=production")
    await create_all()
    async with SessionLocal() as db:
        return await seed_demo(db, reset=reset)
