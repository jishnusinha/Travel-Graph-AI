from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, CostLineItem

# Coherent TG-1047 demo totals
DEMO_ROLE_TOKENS = {
    "supervisor": (2900, 740),
    "destination": (5600, 1250),
    "transport": (4300, 1100),
    "accommodation": (4600, 1250),
    "itinerary": (7600, 2400),
    "aggregator": (3960, 720),
}

# Attributed cost per role INCLUDING tool charges (sums to DEMO_TOTAL_COST)
DEMO_ROLE_COSTS = {
    "supervisor": 0.018,
    "destination": 0.043,
    "transport": 0.038,
    "accommodation": 0.041,
    "itinerary": 0.074,
    "aggregator": 0.023,
}

# Tool charges owned by each role (sums to DEMO_TOOL_COST); the rest of the role cost is model spend
DEMO_ROLE_TOOL_COSTS = {
    "destination": 0.008,
    "transport": 0.006,
    "accommodation": 0.006,
}

DEMO_TOTAL_COST = 0.237
DEMO_MODEL_COST = 0.217
DEMO_TOOL_COST = 0.020
DEMO_INPUT_TOKENS = 28960
DEMO_OUTPUT_TOKENS = 7460
DEMO_WALL_TIME_MS = 14200

COST_EPSILON = 1e-6


def validate_demo_math() -> None:
    assert sum(a + b for a, b in DEMO_ROLE_TOKENS.values()) == DEMO_INPUT_TOKENS + DEMO_OUTPUT_TOKENS
    assert sum(t[0] for t in DEMO_ROLE_TOKENS.values()) == DEMO_INPUT_TOKENS
    assert sum(t[1] for t in DEMO_ROLE_TOKENS.values()) == DEMO_OUTPUT_TOKENS
    assert abs(sum(DEMO_ROLE_COSTS.values()) - DEMO_TOTAL_COST) < 1e-9
    assert abs(DEMO_MODEL_COST + DEMO_TOOL_COST - DEMO_TOTAL_COST) < 1e-9
    assert abs(sum(DEMO_ROLE_TOOL_COSTS.values()) - DEMO_TOOL_COST) < 1e-9
    assert abs(sum(role_model_cost(r) for r in DEMO_ROLE_COSTS) - DEMO_MODEL_COST) < 1e-9


def role_tool_cost(role: str, tool_costs: dict[str, float] | None = None) -> float:
    return float((tool_costs or DEMO_ROLE_TOOL_COSTS).get(role, 0.0))


def role_model_cost(
    role: str,
    role_costs: dict[str, float] | None = None,
    tool_costs: dict[str, float] | None = None,
) -> float:
    """Model-only share of a role's attributed cost (role total minus its tool charges)."""
    total = float((role_costs or DEMO_ROLE_COSTS)[role])
    return round(total - role_tool_cost(role, tool_costs), 6)


def demo_totals_for_nodes(nodes: Iterable[str]) -> dict[str, float | int]:
    """Totals for the subset of role nodes that actually executed (each counted once)."""
    executed = {n for n in nodes if n in DEMO_ROLE_TOKENS}
    tin = sum(DEMO_ROLE_TOKENS[n][0] for n in executed)
    tout = sum(DEMO_ROLE_TOKENS[n][1] for n in executed)
    model = round(sum(role_model_cost(n) for n in executed), 6)
    tool = round(sum(role_tool_cost(n) for n in executed), 6)
    return {
        "input_tokens": tin,
        "output_tokens": tout,
        "model_cost_usd": model,
        "tool_cost_usd": tool,
        "total_cost_usd": round(model + tool, 6),
    }


def apply_demo_accounting(
    run: AgentRun, db: AsyncSession | None = None, executed_nodes: Iterable[str] | None = None
) -> None:
    """Stamp demo token/cost totals on a run.

    With ``executed_nodes`` (a live run), totals cover only the roles that executed, each
    counted once even when a node was retried. Without it, canonical TG-1047 totals apply.
    """
    validate_demo_math()
    if executed_nodes is None:
        run.input_tokens = DEMO_INPUT_TOKENS
        run.output_tokens = DEMO_OUTPUT_TOKENS
        run.model_cost_usd = DEMO_MODEL_COST
        run.tool_cost_usd = DEMO_TOOL_COST
        run.total_cost_usd = DEMO_TOTAL_COST
    else:
        totals = demo_totals_for_nodes(executed_nodes)
        run.input_tokens = int(totals["input_tokens"])
        run.output_tokens = int(totals["output_tokens"])
        run.model_cost_usd = float(totals["model_cost_usd"])
        run.tool_cost_usd = float(totals["tool_cost_usd"])
        run.total_cost_usd = float(totals["total_cost_usd"])
    run.cost_provenance = "demo"
    if run.wall_time_ms <= 0:
        run.wall_time_ms = DEMO_WALL_TIME_MS


async def line_item_totals(db: AsyncSession, run_id: str) -> dict[str, float | int]:
    """Sum persisted cost line items for a run (source of truth for reconciliation)."""
    row = (
        await db.execute(
            select(
                func.coalesce(func.sum(CostLineItem.amount_usd), 0.0),
                func.coalesce(func.sum(CostLineItem.tokens_in), 0),
                func.coalesce(func.sum(CostLineItem.tokens_out), 0),
            ).where(CostLineItem.run_id == run_id)
        )
    ).one()
    return {"amount_usd": round(float(row[0]), 6), "tokens_in": int(row[1]), "tokens_out": int(row[2])}


def reconciles(run_total: float, items_total: float) -> bool:
    return abs(float(run_total) - float(items_total)) <= COST_EPSILON
