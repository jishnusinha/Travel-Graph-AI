from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from app.config import get_settings
from app.graph.state import TravelGraphState
from app.providers.catalog import catalog_provider
from app.providers.llm import get_llm_provider
from app.rag.runtime import offload


GOA_BUDGET = {
    "intercity_travel": 12500,
    "accommodation": 9200,
    "meals": 5400,
    "local_travel": 3650,
    "attractions": 2600,
    "contingency": 1500,
}


_NOT_A_PLACE = {"I", "We", "My", "Our", "The", "A", "An", "Two", "Three", "Four", "Five", "Six", "Me", "Us"}


def _parse_destination(prompt: str, explicit: str | None) -> str | None:
    """Return a destination, or None when it cannot be identified (never guess)."""
    if explicit and explicit.strip():
        return explicit.strip()
    lowered = prompt.lower()
    for key in catalog_provider.list_destinations():
        if re.search(rf"\b{re.escape(key.lower())}\b", lowered):
            return key
    m = re.search(r"\b(?:to|in|visit|visiting)\s+([A-Z][a-zA-Z]+)", prompt)
    if m and m.group(1) not in _NOT_A_PLACE:
        return m.group(1)
    return None


_ISO_DATE_RE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")


def _request_dates(req: dict[str, Any], prompt: str) -> tuple[str | None, str | None]:
    """Dates from structured fields first, then ISO dates written in the prompt."""
    start, end = req.get("start_date"), req.get("end_date")
    if start and end:
        return str(start), str(end)
    found = _ISO_DATE_RE.findall(prompt or "")
    if len(found) >= 2:
        return found[0], found[1]
    return (str(start) if start else None), (str(end) if end else None)


def _day_count(start: str | None, end: str | None, prompt: str) -> int:
    if start and end:
        try:
            s = date.fromisoformat(start)
            e = date.fromisoformat(end)
            return max((e - s).days + 1, 1)
        except ValueError:
            pass
    m = re.search(r"(\d+)\s*-?\s*day", prompt.lower())
    return int(m.group(1)) if m else 5


async def supervisor_node(state: TravelGraphState) -> dict[str, Any]:
    if get_settings().knowledge_mode == "rag":
        from app.services.planner_knowledge import rag_supervisor

        return await offload(rag_supervisor, state)
    req = state.get("trip_request") or {}
    prompt = req.get("prompt") or ""
    destination = _parse_destination(prompt, req.get("destination"))
    travelers = int(req.get("travelers") or 2)
    budget = int(req.get("budget_inr") or 35000)
    req_start, req_end = _request_dates(req, prompt)
    days = _day_count(req_start, req_end, prompt)
    origin = req.get("origin") or "Kolkata, India"
    interests = req.get("interests") or []
    if "beach" in prompt.lower() and "beaches" not in interests:
        interests = list(interests) + ["beaches"]
    if "food" in prompt.lower() and "food" not in interests:
        interests = list(interests) + ["food"]

    missing = []
    if not destination:
        missing.append("destination")
    if budget <= 0:
        missing.append("budget")

    llm = get_llm_provider()
    await llm.complete_json(
        system="You are the TravelGraph supervisor.",
        user=prompt,
        schema_hint="{intent,agents}",
        node_id="supervisor",
    )

    if missing:
        return {
            "needs_clarification": True,
            "clarification_prompt": f"Missing required fields: {', '.join(missing)}",
            "normalized_request": req,
            "messages": [{"role": "supervisor", "content": "clarification required"}],
        }

    date_problem: str | None = None
    if req_start and req_end:
        try:
            if date.fromisoformat(req_end) < date.fromisoformat(req_start):
                date_problem = f"End date {req_end} is before start date {req_start}."
            elif (date.fromisoformat(req_end) - date.fromisoformat(req_start)).days + 1 > 30:
                date_problem = "Trips longer than 30 days are outside the planner's supported range."
        except ValueError:
            date_problem = "Dates must use the YYYY-MM-DD format."
    if date_problem:
        return {
            "needs_clarification": True,
            "clarification_prompt": f"Invalid dates: {date_problem} Please correct the travel dates.",
            "normalized_request": req,
            "messages": [{"role": "supervisor", "content": "clarification required: invalid dates"}],
        }

    start = req_start
    end = req_end
    if not start or not end:
        try:
            start_d = date.fromisoformat(start) if start else date(2027, 1, 12)
        except ValueError:
            start_d = date(2027, 1, 12)
        end_d = start_d + timedelta(days=days - 1)
        start, end = start_d.isoformat(), end_d.isoformat()

    normalized = {
        "destination": destination,
        "origin": origin,
        "travelers": travelers,
        "budget_inr": budget,
        "days": days,
        "start_date": start,
        "end_date": end,
        "interests": interests,
        "prompt": prompt,
    }
    return {
        "needs_clarification": False,
        "normalized_request": normalized,
        "constraints": {
            "budget_inr": budget,
            "days": days,
            "travelers": travelers,
            "interests": interests,
        },
        "messages": [
            {
                "role": "supervisor",
                "content": f"Parsed {days}-day {destination} trip for {travelers} under ₹{budget}",
            }
        ],
        "event_meta": {"selected_agents": ["destination", "transport", "accommodation"]},
    }


async def destination_research_node(state: TravelGraphState) -> dict[str, Any]:
    if get_settings().knowledge_mode == "rag":
        from app.services.planner_knowledge import rag_research

        return await offload(rag_research, state)
    norm = state.get("normalized_request") or {}
    dest = catalog_provider.lookup_destination(norm.get("destination", "Goa"))
    llm = get_llm_provider()
    await llm.complete_json(
        system="Research destinations using only provided catalog facts.",
        user=str(dest.get("attractions")),
        schema_hint="{highlights}",
        node_id="destination",
    )
    return {
        "research": {
            "destination": dest.get("label"),
            "seasonal": dest.get("seasonal"),
            "attractions": dest.get("attractions", []),
            "coords": dest.get("coords", {}),
            "cover": dest.get("cover"),
            "provenance": "local-catalog",
        },
        "travel_advisories": [
            f"Seasonal guidance (catalog): {dest.get('seasonal')}",
            "Estimates only — not live booking inventory.",
        ],
        "tool_results": {"destination_catalog": {"status": "ok", "count": len(dest.get("attractions", []))}},
        "messages": [{"role": "destination", "content": f"Found {len(dest.get('attractions', []))} attractions"}],
    }


async def transport_node(state: TravelGraphState) -> dict[str, Any]:
    if get_settings().knowledge_mode == "rag":
        from app.services.planner_knowledge import rag_transport

        return await offload(rag_transport, state)
    norm = state.get("normalized_request") or {}
    dest = catalog_provider.lookup_destination(norm.get("destination", "Goa"))
    options = dest.get("transport") or []
    llm = get_llm_provider()
    await llm.complete_json(
        system="Select transport options from catalog samples.",
        user=str(options),
        schema_hint="{selected}",
        node_id="transport",
    )
    return {
        "transport_options": options,
        "tool_results": {"transport_catalog": {"status": "ok", "options": len(options)}},
        "messages": [{"role": "transport", "content": f"{len(options)} sample transport options"}],
    }


async def accommodation_node(state: TravelGraphState) -> dict[str, Any]:
    if get_settings().knowledge_mode == "rag":
        from app.services.planner_knowledge import rag_stay

        return await offload(rag_stay, state)
    norm = state.get("normalized_request") or {}
    dest = catalog_provider.lookup_destination(norm.get("destination", "Goa"))
    hotels = dest.get("hotels") or []
    budget = int(norm.get("budget_inr") or 35000)
    affordable = [h for h in hotels if h.get("total_inr", 0) <= budget * 0.4] or hotels
    llm = get_llm_provider()
    await llm.complete_json(
        system="Recommend stays from catalog.",
        user=str(affordable),
        schema_hint="{selected}",
        node_id="accommodation",
    )
    return {
        "accommodation_options": affordable,
        "tool_results": {"hotel_catalog": {"status": "ok", "options": len(affordable)}},
        "messages": [{"role": "accommodation", "content": f"Compared {len(affordable)} hotels within budget heuristics"}],
    }


def _goa_itinerary() -> list[dict[str, Any]]:
    return [
        {
            "day_number": 1,
            "title": "Arrival & North Goa",
            "summary": "Beaches, relaxation & local experiences",
            "area": "North Goa",
            "meta": {"arrival": "GOI (Goa Airport)", "check_in": "2:00 PM"},
            "activities": [
                {"time_label": "11:00 AM", "category": "transport", "title": "Arrive in Goa & Transfer", "description": "Transfer to your hotel in North Goa", "estimated_cost_inr": 800},
                {"time_label": "2:00 PM", "category": "hotel", "title": "Check-in & refresh", "description": "Settle in and enjoy some downtime", "estimated_cost_inr": 0},
                {"time_label": "4:00 PM", "category": "beach", "title": "Calangute Beach", "description": "Explore the coast and unwind", "estimated_cost_inr": 0},
                {"time_label": "6:30 PM", "category": "beach", "title": "Sunset at Baga Beach", "description": "A scenic end to your first day", "estimated_cost_inr": 0},
                {"time_label": "8:00 PM", "category": "food", "title": "Dinner at a Beach Shack", "description": "Local Goan seafood", "estimated_cost_inr": 1200},
            ],
        },
        {
            "day_number": 2,
            "title": "Beaches & Forts",
            "summary": "North Goa highlights",
            "area": "North Goa",
            "activities": [
                {"time_label": "9:30 AM", "category": "sightseeing", "title": "Fort Aguada", "description": "Coastal fort views", "estimated_cost_inr": 50},
                {"time_label": "1:00 PM", "category": "food", "title": "Goan thali lunch", "description": "Local cuisine", "estimated_cost_inr": 800},
                {"time_label": "4:00 PM", "category": "beach", "title": "Anjuna Beach", "description": "Relaxed afternoon", "estimated_cost_inr": 0},
            ],
        },
        {
            "day_number": 3,
            "title": "Old Goa & Panaji",
            "summary": "Culture & food",
            "area": "Panaji / Old Goa",
            "activities": [
                {"time_label": "10:00 AM", "category": "culture", "title": "Basilica of Bom Jesus", "description": "Heritage visit", "estimated_cost_inr": 0},
                {"time_label": "1:00 PM", "category": "food", "title": "Fontainhas cafe lunch", "description": "Latin Quarter stroll", "estimated_cost_inr": 900},
                {"time_label": "5:00 PM", "category": "sightseeing", "title": "Mandovi riverfront", "description": "Evening walk", "estimated_cost_inr": 200},
            ],
        },
        {
            "day_number": 4,
            "title": "South Goa",
            "summary": "Quiet beaches",
            "area": "South Goa",
            "activities": [
                {"time_label": "10:00 AM", "category": "beach", "title": "Palolem Beach", "description": "South Goa coastline", "estimated_cost_inr": 0},
                {"time_label": "1:30 PM", "category": "food", "title": "Beachside lunch", "description": "Seafood shack", "estimated_cost_inr": 1100},
                {"time_label": "4:00 PM", "category": "nature", "title": "Colva / Cabo de Rama outlook", "description": "Scenic stop", "estimated_cost_inr": 300},
            ],
        },
        {
            "day_number": 5,
            "title": "Checkout & Departure",
            "summary": "Souvenirs and flight home",
            "area": "North Goa / Airport",
            "activities": [
                {"time_label": "9:00 AM", "category": "shopping", "title": "Local market souvenirs", "description": "Light shopping", "estimated_cost_inr": 800},
                {"time_label": "12:00 PM", "category": "hotel", "title": "Checkout", "description": "Hotel checkout", "estimated_cost_inr": 0},
                {"time_label": "3:00 PM", "category": "transport", "title": "Transfer to GOI & depart", "description": "Airport transfer", "estimated_cost_inr": 800},
            ],
        },
    ]


def _generic_itinerary(dest_name: str, days: int, attractions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Catalog-driven day plan: arrival, 1-2 sights/day, lunch + dinner, departure on last day.

    Meal estimates (500 + 700) match the 1,200/day meals line in the budget breakdown.
    """
    fallback = {"name": f"Explore {dest_name}", "area": dest_name, "est_cost": 0}
    pool = attractions or [fallback]
    cursor = 0
    out: list[dict[str, Any]] = []
    for i in range(1, days + 1):
        first = pool[cursor % len(pool)]
        cursor += 1
        second = pool[cursor % len(pool)] if len(pool) > 1 and 1 < i < days else None
        if second is not None:
            cursor += 1
        area = first.get("area", dest_name)
        activities: list[dict[str, Any]] = []

        def add(time_label: str, category: str, title: str, description: str, cost: int) -> None:
            activities.append(
                {
                    "time_label": time_label,
                    "category": category,
                    "title": title,
                    "description": description,
                    "estimated_cost_inr": cost,
                }
            )

        if i == 1:
            add("11:00 AM", "transport", f"Arrive in {dest_name} & transfer", "Transfer to your stay", 700)
            add("2:00 PM", "hotel", "Check-in & refresh", "Settle in and rest", 0)
            add("4:00 PM", "sightseeing", first["name"], "Catalog-based activity estimate", int(first.get("est_cost") or 0))
            add("7:30 PM", "food", "Dinner nearby", "Local cuisine", 700)
            title = f"Arrival & {area}"
        elif i == days:
            add("9:30 AM", "sightseeing", first["name"], "Catalog-based activity estimate", int(first.get("est_cost") or 0))
            add("1:00 PM", "food", "Farewell lunch", "Local cuisine", 500)
            add("3:30 PM", "transport", f"Checkout & depart {dest_name}", "Transfer to station/airport", 700)
            title = "Checkout & Departure"
        else:
            add("9:30 AM", "sightseeing", first["name"], "Catalog-based activity estimate", int(first.get("est_cost") or 0))
            add("1:00 PM", "food", "Local lunch", "Regional specialties", 500)
            if second is not None:
                add("3:30 PM", "sightseeing", second["name"], "Catalog-based activity estimate", int(second.get("est_cost") or 0))
            add("7:30 PM", "food", "Dinner nearby", "Local cuisine", 700)
            title = f"{area} highlights"
        out.append(
            {
                "day_number": i,
                "title": title,
                "summary": f"{first['name']}" + (f" & {second['name']}" if second else ""),
                "area": area,
                "activities": activities,
            }
        )
    return out


async def itinerary_node(state: TravelGraphState) -> dict[str, Any]:
    if get_settings().knowledge_mode == "rag":
        from app.services.planner_knowledge import rag_itinerary

        return await offload(rag_itinerary, state)
    norm = state.get("normalized_request") or {}
    dest_name = norm.get("destination", "Goa")
    days = int(norm.get("days") or 5)
    llm = get_llm_provider()
    await llm.complete_json(
        system="Build a day-by-day itinerary from research.",
        user=str({"destination": dest_name, "days": days, "research": state.get("research")}),
        schema_hint="{days}",
        node_id="itinerary",
    )

    if dest_name.lower().startswith("goa") and days == 5:
        itinerary = _goa_itinerary()
        budget = dict(GOA_BUDGET)
    else:
        research = state.get("research") or {}
        attractions = research.get("attractions") or []
        hotels = state.get("accommodation_options") or []
        transport = state.get("transport_options") or []
        hotel_cost = hotels[0]["total_inr"] if hotels else 9000
        transport_cost = transport[0]["total_inr"] if transport else 10000
        itinerary = _generic_itinerary(dest_name, days, attractions)
        meals = 1200 * days
        local = 600 * days
        attractions_cost = sum(int(a.get("est_cost") or 0) for a in attractions[:days])
        contingency = 1500
        budget = {
            "intercity_travel": transport_cost,
            "accommodation": hotel_cost,
            "meals": meals,
            "local_travel": local,
            "attractions": attractions_cost,
            "contingency": contingency,
        }

    total = sum(budget.values())
    budget["total"] = total
    budget["remaining"] = int(norm.get("budget_inr") or 35000) - total
    return {
        "itinerary_days": itinerary,
        "budget_breakdown": budget,
        "messages": [{"role": "itinerary", "content": f"Built {len(itinerary)}-day plan totaling ₹{total}"}],
    }


async def validator_node(state: TravelGraphState) -> dict[str, Any]:
    """Deterministic Python validator — not an LLM agent."""
    findings: list[dict[str, Any]] = []
    norm = state.get("normalized_request") or {}
    days = state.get("itinerary_days") or []
    budget = state.get("budget_breakdown") or {}
    expected_days = int(norm.get("days") or 0)
    trip_budget = int(norm.get("budget_inr") or 0)

    if expected_days and len(days) != expected_days:
        findings.append(
            {
                "code": "day_count_mismatch",
                "severity": "error",
                "message": f"Expected {expected_days} days, got {len(days)}",
                "correctable": True,
            }
        )
    for d in days:
        if not d.get("activities"):
            findings.append(
                {
                    "code": "empty_day",
                    "severity": "error",
                    "message": f"Day {d.get('day_number')} has no activities",
                    "correctable": True,
                }
            )
    if budget.get("verification_status") == "unknown":
        findings.append(
            {
                "code": "budget_unverified",
                "severity": "warning",
                "message": "Budget fit is unknown. Missing estimates were not treated as zero.",
                "correctable": False,
            }
        )
    else:
        total = int(budget.get("total") or 0)
        if trip_budget and total > trip_budget:
            findings.append(
                {
                    "code": "budget_exceeded",
                    "severity": "error",
                    "message": f"Estimated ₹{total} exceeds budget ₹{trip_budget}",
                    "correctable": True,
                }
            )
    seen_titles: dict[str, int] = {}
    for day in days:
        for activity in day.get("activities") or []:
            category = activity.get("category")
            title = " ".join(str(activity.get("title") or "").casefold().split())
            if category in {"transport", "note"} or not title:
                continue
            if title in seen_titles:
                findings.append(
                    {
                        "code": "duplicate_attraction",
                        "severity": "warning",
                        "message": f"{activity.get('title')} is scheduled more than once.",
                        "correctable": False,
                    }
                )
            else:
                seen_titles[title] = int(day.get("day_number") or 0)
            if get_settings().knowledge_mode == "rag" and not activity.get("citation_ids"):
                findings.append(
                    {
                        "code": "uncited_activity",
                        "severity": "warning",
                        "message": f"{activity.get('title')} has no supporting excerpt.",
                        "correctable": False,
                    }
                )
    for day in days:
        if day.get("geo_warning"):
            findings.append(
                {
                    "code": "geo_span_straight_line",
                    "severity": "warning",
                    "message": day["geo_warning"],
                    "correctable": False,
                }
            )
    if not state.get("transport_options"):
        findings.append({"code": "missing_transport", "severity": "warning", "message": "No transport options", "correctable": False})
    if not state.get("accommodation_options"):
        findings.append({"code": "missing_stay", "severity": "warning", "message": "No accommodation options", "correctable": False})

    parts = ["intercity_travel", "accommodation", "meals", "local_travel", "attractions", "contingency"]
    if budget.get("verification_status") != "unknown" and all(p in budget for p in parts):
        recomputed = sum(int(budget[p]) for p in parts)
        if recomputed != int(budget.get("total") or -1):
            findings.append(
                {
                    "code": "budget_math",
                    "severity": "error",
                    "message": "Budget parts do not sum to total",
                    "correctable": True,
                }
            )

    retry = int(state.get("retry_count") or 0)
    hard_errors = [f for f in findings if f.get("severity") == "error" and f.get("correctable")]
    return {
        "validation_findings": findings,
        "retry_count": retry + (1 if hard_errors else 0),
        "messages": [{"role": "validator", "content": f"{len(findings)} findings"}],
    }


async def aggregator_node(state: TravelGraphState) -> dict[str, Any]:
    if get_settings().knowledge_mode == "rag":
        from app.services.planner_knowledge import ground_plan, rag_aggregate

        base = await offload(rag_aggregate, state)
        plan = await ground_plan(base["final_plan"])
        return {"final_plan": plan, "messages": base.get("messages") or []}
    norm = state.get("normalized_request") or {}
    budget = state.get("budget_breakdown") or {}
    hotels = state.get("accommodation_options") or []
    transport = state.get("transport_options") or []
    llm = get_llm_provider()
    narrative = await llm.complete_json(
        system="Summarize the final travel plan for the traveler.",
        user=str({"destination": norm.get("destination"), "budget": budget}),
        schema_hint="{summary}",
        node_id="aggregator",
    )
    title = f"{norm.get('destination', 'Trip')} Escape Plan"
    if str(norm.get("destination", "")).lower().startswith("goa"):
        title = "Goa Escape Plan"
    final = {
        "title": title,
        "destination": norm.get("destination"),
        "origin": norm.get("origin"),
        "start_date": norm.get("start_date"),
        "end_date": norm.get("end_date"),
        "travelers": norm.get("travelers"),
        "budget_inr": norm.get("budget_inr"),
        "estimated_cost_inr": budget.get("total"),
        "budget_breakdown": budget,
        "days": state.get("itinerary_days") or [],
        "transport": transport[0] if transport else {},
        "accommodation": hotels[0] if hotels else {},
        "research": state.get("research") or {},
        "advisories": state.get("travel_advisories") or [],
        "validation_findings": state.get("validation_findings") or [],
        "recommendation": (
            "The plan is within your budget based on local catalog estimates. "
            "You can optionally upgrade your stay or add a watersports activity on Day 2."
            if int(budget.get("remaining") or 0) >= 0
            else "Estimated costs exceed the stated budget — consider adjusting dates or lodging."
        ),
        "narrative": narrative.get("narrative") or narrative.get("summary") or "Plan ready.",
        "provenance": "local-catalog + demo/openai agents — estimates only",
    }
    return {
        "final_plan": final,
        "messages": [{"role": "aggregator", "content": "Final plan compiled"}],
    }


def route_after_supervisor(state: TravelGraphState) -> str:
    if state.get("needs_clarification"):
        return "end_clarify"
    return "fanout"


def route_after_validator(state: TravelGraphState) -> str:
    findings = state.get("validation_findings") or []
    hard = [f for f in findings if f.get("severity") == "error" and f.get("correctable")]
    retry = int(state.get("retry_count") or 0)
    if hard and retry <= 2:
        return "itinerary"
    return "aggregator"
