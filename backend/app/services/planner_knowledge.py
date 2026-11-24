"""RAG-mode planning. Catalog mode does not call this module.

Costs come only from stored estimates. Missing numbers stay unknown.
"""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import get_settings
from app.rag.store import active_snapshot, connect, corpus_stats, haversine_km, search_sync
from app.services.discovery_service import discover


def rag_supervisor(state: dict[str, Any]) -> dict[str, Any]:
    from app.graph.nodes import _day_count, _request_dates

    req = state.get("trip_request") or {}
    prompt = req.get("prompt") or ""
    stats = corpus_stats()
    if stats.get("status") != "ready":
        return {
            "needs_clarification": True,
            "clarification_prompt": (
                "Knowledge mode is rag, but no active snapshot is installed. "
                "Run .\\scripts\\ingest.ps1 or set KNOWLEDGE_MODE=catalog for the legacy demo."
            ),
            "normalized_request": req,
            "discovery_candidates": [],
            "messages": [{"role": "supervisor", "content": "snapshot missing"}],
        }
    explicit = (req.get("destination") or "").strip()
    resolved = _resolve(explicit or prompt)
    travelers = int(req.get("travelers") or 2)
    budget = int(req.get("budget_inr") or 0)
    start, end = _request_dates(req, prompt)
    days = _day_count(start, end, prompt)
    if not resolved:
        preview = discover(query=prompt, user_id=state.get("user_id") or "anonymous", filters=req)
        return {
            "needs_clarification": True,
            "clarification_prompt": "No destination was named. Choose one of the retrieved places or name a destination.",
            "normalized_request": req,
            "discovery_candidates": preview.get("results") or [],
            "snapshot_id": stats.get("snapshot_id"),
            "messages": [{"role": "supervisor", "content": "clarification required"}],
        }
    if budget <= 0:
        return {
            "needs_clarification": True,
            "clarification_prompt": "Missing required fields: budget",
            "normalized_request": req,
            "messages": [{"role": "supervisor", "content": "clarification required"}],
        }
    from datetime import date

    if start and end:
        try:
            if date.fromisoformat(end) < date.fromisoformat(start):
                return _date_problem(req, f"End date {end} is before start date {start}.")
            if (date.fromisoformat(end) - date.fromisoformat(start)).days + 1 > 30:
                return _date_problem(req, "Trips longer than 30 days are outside the planner's supported range.")
        except ValueError:
            return _date_problem(req, "Dates must use the YYYY-MM-DD format.")
    if not start or not end:
        start_d = date.fromisoformat(start) if start else date(2027, 1, 12)
        end_d = start_d.fromordinal(start_d.toordinal() + days - 1)
        start, end = start_d.isoformat(), end_d.isoformat()
    normalized = {
        "destination": resolved["name"],
        "destination_id": resolved["id"],
        "destination_slug": resolved["slug"],
        "origin": req.get("origin") or "Kolkata, India",
        "travelers": travelers,
        "budget_inr": budget,
        "days": days,
        "start_date": start,
        "end_date": end,
        "interests": req.get("interests") or [],
        "prompt": prompt,
        "knowledge_mode": "rag",
    }
    return {
        "needs_clarification": False,
        "normalized_request": normalized,
        "snapshot_id": stats.get("snapshot_id"),
        "constraints": {"budget_inr": budget, "days": days, "travelers": travelers},
        "messages": [{"role": "supervisor", "content": f"Parsed {days}-day {resolved['name']} from the knowledge snapshot"}],
        "event_meta": {"selected_agents": ["destination", "transport", "accommodation"], "knowledge_mode": "rag"},
    }


def rag_research(state: dict[str, Any]) -> dict[str, Any]:
    norm = state.get("normalized_request") or {}
    slug = norm.get("destination_slug")
    found = search_sync(
        query=norm.get("prompt") or norm.get("destination") or "",
        user_id=state.get("user_id") or "planner",
        filters={"destination_slug": slug} if slug else {},
        mode="evidence",
        node_id="destination",
        agent_run_id=state.get("run_id"),
    )
    attractions = _attractions(norm.get("destination_id"))
    cited = []
    evidence = found.get("evidence") or []
    for attraction in attractions:
        match = next((ev for ev in evidence if attraction["name"].lower() in (ev.get("text") or "").lower()), None)
        cited.append({**attraction, "citation_id": match.get("citation_id") if match else None})
    return {
        "research": {
            "destination": norm.get("destination"),
            "destination_id": norm.get("destination_id"),
            "slug": slug,
            "attractions": cited,
            "evidence": evidence,
            "snapshot_id": found.get("snapshot_id"),
            "embedding_kind": found.get("embedding_kind"),
            "provenance": "local-retrieval",
            "generation_mode": "deterministic_evidence",
        },
        "travel_advisories": [
            "Plan text is retrieved from the active snapshot and composed without an LLM."
            if get_settings().ai_mode == "demo"
            else "Retrieved evidence is local. Optional model output is validated against those excerpts.",
            "Current closures, permits and live prices are unknown unless a source in the snapshot says so.",
        ],
        "tool_results": {
            "knowledge_retrieve": {
                "status": found.get("status"),
                "count": len(evidence),
                "duration_ms": (found.get("timings_ms") or {}).get("total_ms", 0),
                "strategy": found.get("strategy_applied"),
                "retrieval_run_id": found.get("retrieval_run_id"),
            }
        },
        "messages": [{"role": "destination", "content": f"Retrieved {len(evidence)} evidence chunks"}],
    }


def rag_transport(state: dict[str, Any]) -> dict[str, Any]:
    norm = state.get("normalized_request") or {}
    estimates = _estimates(norm.get("destination_id"), "transport")
    options = [_estimate_option(est, "transport") for est in estimates]
    return {
        "transport_options": options,
        "tool_results": {"knowledge_transport": {"status": "ok" if options else "unknown", "options": len(options)}},
        "messages": [{"role": "transport", "content": f"{len(options)} sourced transport estimates"}],
    }


def rag_stay(state: dict[str, Any]) -> dict[str, Any]:
    norm = state.get("normalized_request") or {}
    estimates = _estimates(norm.get("destination_id"), "accommodation")
    options = [_estimate_option(est, "accommodation") for est in estimates]
    return {
        "accommodation_options": options,
        "tool_results": {"knowledge_stay": {"status": "ok" if options else "unknown", "options": len(options)}},
        "messages": [{"role": "accommodation", "content": f"{len(options)} sourced stay estimates"}],
    }


def rag_itinerary(state: dict[str, Any]) -> dict[str, Any]:
    norm = state.get("normalized_request") or {}
    research = state.get("research") or {}
    days_n = int(norm.get("days") or 1)
    attractions = list(research.get("attractions") or [])
    if not attractions:
        attractions = _names_in_evidence(research.get("evidence") or [])
    ordered = _order_attractions(attractions)
    evidence = research.get("evidence") or []
    fallback_citation = evidence[0]["citation_id"] if evidence else None
    days = []
    cursor = 0
    for day_number in range(1, days_n + 1):
        activities = []
        if day_number == 1:
            activities.append(_activity("11:00", "transport", f"Arrive in {norm.get('destination')}", "Arrival is a planning placeholder. A driving or flight route was not retrieved.", None, "unknown"))
        if ordered:
            take = 1 if day_number in {1, days_n} else 2
            for _ in range(take):
                if cursor >= len(ordered):
                    break
                item = ordered[cursor]
                cursor += 1
                activities.append(
                    _activity(
                        "09:30" if not activities else "14:00",
                        item.get("category") or "sightseeing",
                        item["name"],
                        "Scheduled from a named attraction in the snapshot.",
                        item.get("citation_id") or fallback_citation,
                        "source_named" if item.get("citation_id") or fallback_citation else "unknown",
                        lat=item.get("lat"),
                        lon=item.get("lon"),
                        attraction_id=item.get("id"),
                    )
                )
        else:
            activities.append(
                _activity(
                    "10:00",
                    "note",
                    "No sourced attractions in the active snapshot",
                    "The planner did not invent sights.",
                    fallback_citation,
                    "unknown",
                )
            )
        if day_number == days_n:
            activities.append(_activity("16:00", "transport", f"Depart {norm.get('destination')}", "Departure transfer price is unknown unless an estimate is stored.", None, "unknown"))
        span = _span_warning(activities)
        days.append(
            {
                "day_number": day_number,
                "title": f"Day {day_number}",
                "summary": ", ".join(a["title"] for a in activities if a["category"] not in {"transport"}) or "Open day",
                "area": norm.get("destination") or "",
                "activities": activities,
                "geo_warning": span,
            }
        )
    budget = _budget(norm, state.get("transport_options") or [], state.get("accommodation_options") or [])
    return {
        "itinerary_days": days,
        "budget_breakdown": budget,
        "messages": [{"role": "itinerary", "content": f"Built {len(days)}-day evidence itinerary"}],
    }


def rag_aggregate(state: dict[str, Any]) -> dict[str, Any]:
    norm = state.get("normalized_request") or {}
    budget = state.get("budget_breakdown") or {}
    research = state.get("research") or {}
    unknown = budget.get("verification_status") == "unknown"
    final = {
        "title": f"{norm.get('destination', 'Trip')} plan",
        "destination": norm.get("destination"),
        "destination_id": norm.get("destination_id"),
        "origin": norm.get("origin"),
        "start_date": norm.get("start_date"),
        "end_date": norm.get("end_date"),
        "travelers": norm.get("travelers"),
        "budget_inr": norm.get("budget_inr"),
        "estimated_cost_inr": budget.get("total"),
        "budget_breakdown": budget,
        "days": state.get("itinerary_days") or [],
        "transport": (state.get("transport_options") or [{}])[0],
        "accommodation": (state.get("accommodation_options") or [{}])[0],
        "research": {
            "cover": "",
            "provenance": "local-retrieval",
            "snapshot_id": research.get("snapshot_id"),
            "evidence": research.get("evidence") or [],
        },
        "snapshot_id": research.get("snapshot_id") or state.get("snapshot_id"),
        "advisories": state.get("travel_advisories") or [],
        "validation_findings": state.get("validation_findings") or [],
        "citations": [ev.get("citation_id") for ev in (research.get("evidence") or []) if ev.get("citation_id")],
        "recommendation": (
            "Budget fit is unknown because the snapshot has no applicable cost estimate."
            if unknown
            else "Totals use stored estimate ranges, not live booking prices."
        ),
        "narrative": "Deterministic evidence composition. This text was not produced by a language model.",
        "provenance": "local-retrieval",
        "generation_mode": "deterministic_evidence",
        "embedding_kind": research.get("embedding_kind"),
    }
    return {"final_plan": final, "messages": [{"role": "aggregator", "content": "Evidence plan compiled"}]}


def _resolve(text: str) -> dict[str, Any] | None:
    conn = connect()
    try:
        if active_snapshot(conn) is None and not text:
            return None
        rows = conn.execute("SELECT id, slug, name, aliases FROM destinations").fetchall()
    finally:
        conn.close()
    lowered = (text or "").lower()
    best = None
    for row in rows:
        names = [row["name"], row["slug"]]
        try:
            names.extend(json.loads(row["aliases"] or "[]"))
        except json.JSONDecodeError:
            pass
        for name in names:
            token = str(name).lower().strip()
            if token and token in lowered and (best is None or len(token) > len(best["name"])):
                best = {"id": row["id"], "slug": row["slug"], "name": row["name"]}
    return best


def _date_problem(req: dict, message: str) -> dict[str, Any]:
    return {
        "needs_clarification": True,
        "clarification_prompt": f"Invalid dates: {message} Please correct the travel dates.",
        "normalized_request": req,
        "messages": [{"role": "supervisor", "content": "clarification required: invalid dates"}],
    }


def _attractions(destination_id: str | None) -> list[dict[str, Any]]:
    if not destination_id:
        return []
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT id, name, category, lat, lon, coordinate_status FROM attractions WHERE destination_id = ? ORDER BY name",
            (destination_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _estimates(destination_id: str | None, category: str) -> list[dict[str, Any]]:
    if not destination_id:
        return []
    conn = connect()
    try:
        rows = conn.execute(
            """
            SELECT * FROM travel_cost_estimates
            WHERE destination_id = ? AND lower(category) = ?
            """,
            (destination_id, category.lower()),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _estimate_option(est: dict[str, Any], kind: str) -> dict[str, Any]:
    low, high = est.get("low_inr"), est.get("high_inr")
    return {
        "name": f"{kind} estimate",
        "label": f"{kind} estimate ({est.get('basis') or 'unspecified basis'})",
        "low_inr": low,
        "high_inr": high,
        "total_inr": high if high is not None else low,
        "basis": est.get("basis"),
        "method": est.get("method"),
        "confidence": est.get("confidence"),
        "provenance": "stored-estimate",
        "verification_status": "estimate",
    }


def _activity(time_label, category, title, description, citation_id, status, lat=None, lon=None, attraction_id=None) -> dict:
    return {
        "time_label": time_label,
        "category": category,
        "title": title,
        "description": description,
        "estimated_cost_inr": 0,
        "verification_status": status,
        "citation_ids": [citation_id] if citation_id else [],
        "lat": lat,
        "lon": lon,
        "attraction_id": attraction_id,
        "cost_basis": None,
    }


_NAMED = re.compile(
    r"\b([A-Z][A-Za-z'’.-]+(?:\s+[A-Z][A-Za-z'’.-]+){0,3}\s(?:Falls|Beach|Temple|Lake|Fort|Park|Museum|Peak|Waterfall))\b"
)


def _names_in_evidence(evidence: list[dict]) -> list[dict]:
    """Place names that literally occur in retrieved text. No coordinates are guessed."""
    found: list[dict] = []
    seen: set[str] = set()
    for item in evidence:
        for match in _NAMED.finditer(item.get("text") or ""):
            name = match.group(1)
            if name in seen:
                continue
            seen.add(name)
            found.append(
                {
                    "name": name,
                    "category": "mentioned",
                    "citation_id": item.get("citation_id"),
                    "lat": None,
                    "lon": None,
                }
            )
            if len(found) >= 8:
                return found
    return found


def _order_attractions(items: list[dict]) -> list[dict]:
    located = [i for i in items if i.get("lat") is not None and i.get("lon") is not None]
    rest = [i for i in items if i not in located]
    if not located:
        return items
    current = located[0]
    ordered = [current]
    pool = located[1:]
    while pool:
        nxt = min(pool, key=lambda item: haversine_km(current["lat"], current["lon"], item["lat"], item["lon"]))
        ordered.append(nxt)
        pool.remove(nxt)
        current = nxt
    return ordered + rest


def _span_warning(activities: list[dict]) -> str | None:
    points = [(a["lat"], a["lon"]) for a in activities if a.get("lat") is not None and a.get("lon") is not None]
    for i in range(len(points) - 1):
        km = haversine_km(points[i][0], points[i][1], points[i + 1][0], points[i + 1][1])
        if km > 150:
            return f"Straight-line separation is {km:.0f} km. This is not a driving route."
    return None


def _budget(norm: dict, transport: list[dict], stays: list[dict]) -> dict[str, Any]:
    def amount(options: list[dict]) -> int | None:
        if not options or options[0].get("total_inr") is None:
            return None
        return int(options[0]["total_inr"])

    parts = {
        "intercity_travel": amount(transport),
        "accommodation": amount(stays),
        "meals": None,
        "local_travel": None,
        "attractions": None,
        "contingency": None,
    }
    known = [v for v in parts.values() if isinstance(v, int)]
    if len(known) != len(parts):
        return {
            **parts,
            "total": None,
            "remaining": None,
            "verification_status": "unknown",
            "note": "One or more cost categories have no stored estimate. They are not treated as zero.",
        }
    total = sum(known)
    return {
        **parts,
        "total": total,
        "remaining": int(norm.get("budget_inr") or 0) - total,
        "verification_status": "estimate",
        "note": "Stored estimates only. Not a live fare or hotel quote.",
    }
