from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from app.schemas.common import APIModel


class RunCreateIn(APIModel):
    trip_id: Optional[str] = None
    prompt: str = Field(min_length=8, max_length=2000)
    destination: Optional[str] = None
    origin: str = "Kolkata, India"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    travelers: int = 2
    budget_inr: int = 35000
    interests: list[str] = Field(default_factory=list)


class AgentEventOut(APIModel):
    id: str
    run_id: str
    seq: int
    ts: datetime
    type: str
    node_id: Optional[str] = None
    status: Optional[str] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class RunOut(APIModel):
    id: str
    public_id: str
    trip_id: Optional[str] = None
    thread_id: str
    status: str
    prompt: str
    request_payload: dict[str, Any] = Field(default_factory=dict)
    final_plan: dict[str, Any] = Field(default_factory=dict)
    ai_mode: str
    model_name: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    wall_time_ms: int
    input_tokens: int
    output_tokens: int
    model_cost_usd: float
    tool_cost_usd: float
    total_cost_usd: float
    cost_provenance: str
    error_message: Optional[str] = None
    revision_number: int
    created_at: datetime


class RunListItem(APIModel):
    id: str
    public_id: str
    trip_id: Optional[str] = None
    trip_title: Optional[str] = None
    status: str
    prompt: str
    ai_mode: str
    model_name: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    wall_time_ms: int
    input_tokens: int
    output_tokens: int
    total_cost_usd: float
    cost_provenance: str
    revision_number: int
    created_at: datetime


class GraphNodeOut(APIModel):
    id: str
    label: str
    status: str
    duration_ms: Optional[int] = None
    role: str
    invocations: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: Optional[float] = None
    summary: Optional[str] = None


class GraphEdgeOut(APIModel):
    id: str
    source: str
    target: str


class GraphOut(APIModel):
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    current_node: Optional[str] = None
    run_status: Optional[str] = None
    last_seq: int = 0


class NodeDetailOut(APIModel):
    node_id: str
    status: str
    events: list[AgentEventOut] = Field(default_factory=list)
    model_invocations: list[dict[str, Any]] = Field(default_factory=list)
    tool_invocations: list[dict[str, Any]] = Field(default_factory=list)
    cost_items: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
