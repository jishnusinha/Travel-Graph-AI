from __future__ import annotations

import operator
from typing import Annotated, Any, Optional, TypedDict


def merge_dicts(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a or {})
    out.update(b or {})
    return out


class TravelGraphState(TypedDict, total=False):
    user_id: str
    trip_id: Optional[str]
    thread_id: str
    run_id: str
    trip_request: dict[str, Any]
    normalized_request: dict[str, Any]
    constraints: dict[str, Any]
    research: dict[str, Any]
    transport_options: list[dict[str, Any]]
    accommodation_options: list[dict[str, Any]]
    itinerary_days: list[dict[str, Any]]
    budget_breakdown: dict[str, Any]
    travel_advisories: list[str]
    validation_findings: list[dict[str, Any]]
    messages: Annotated[list[dict[str, Any]], operator.add]
    agent_errors: Annotated[list[dict[str, Any]], operator.add]
    tool_results: Annotated[dict[str, Any], merge_dicts]
    final_plan: dict[str, Any]
    revision_number: int
    replan_requests: list[dict[str, Any]]
    needs_clarification: bool
    clarification_prompt: str
    retry_count: int
    event_meta: dict[str, Any]
