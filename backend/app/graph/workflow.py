from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    accommodation_node,
    aggregator_node,
    destination_research_node,
    itinerary_node,
    route_after_supervisor,
    route_after_validator,
    supervisor_node,
    transport_node,
    validator_node,
)
from app.graph.state import TravelGraphState


def build_travel_graph(checkpointer: Any | None = None):
    """
    START -> supervisor -> parallel(destination, transport, accommodation)
          -> itinerary -> validator -> (loop itinerary | aggregator) -> END
    """
    return _build_with_fanout(checkpointer)


def _build_with_fanout(checkpointer: Any | None = None):
    g: StateGraph = StateGraph(TravelGraphState)
    g.add_node("supervisor", supervisor_node)
    g.add_node("destination", destination_research_node)
    g.add_node("transport", transport_node)
    g.add_node("accommodation", accommodation_node)
    g.add_node("itinerary", itinerary_node)
    g.add_node("validator", validator_node)
    g.add_node("aggregator", aggregator_node)

    def fanout_gate(state: TravelGraphState) -> dict:
        return {}

    g.add_node("fanout", fanout_gate)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"end_clarify": END, "fanout": "fanout"},
    )
    g.add_edge("fanout", "destination")
    g.add_edge("fanout", "transport")
    g.add_edge("fanout", "accommodation")
    # Join: itinerary waits for ALL three specialists (barrier), not just the first to finish
    g.add_edge(["destination", "transport", "accommodation"], "itinerary")
    g.add_edge("itinerary", "validator")
    g.add_conditional_edges(
        "validator",
        route_after_validator,
        {"itinerary": "itinerary", "aggregator": "aggregator"},
    )
    g.add_edge("aggregator", END)

    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


GRAPH_NODES = [
    "supervisor",
    "destination",
    "transport",
    "accommodation",
    "itinerary",
    "validator",
    "aggregator",
]

GRAPH_EDGES = [
    ("supervisor", "destination"),
    ("supervisor", "transport"),
    ("supervisor", "accommodation"),
    ("destination", "itinerary"),
    ("transport", "itinerary"),
    ("accommodation", "itinerary"),
    ("itinerary", "validator"),
    ("validator", "aggregator"),
    ("validator", "itinerary"),
]
