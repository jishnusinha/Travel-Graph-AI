"""Deterministic query understanding. Unknown fields stay null."""

from __future__ import annotations

import re
from typing import Any

_BUDGET = re.compile(
    r"(?:₹|rs\.?|inr)?\s*(\d{1,3}(?:,\d{3})+|\d+)\s*(k)?",
    re.I,
)
_DAYS_WORD = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_TRAVELERS = re.compile(r"\b(\d{1,2})\s*(?:travellers|travelers|people|adults|persons)\b", re.I)
_ORIGIN = re.compile(r"\bfrom\s+([A-Za-z][A-Za-z .'-]{1,40})", re.I)
_DAYS_NUM = re.compile(r"\b(\d{1,2})\s*-?\s*days?\b", re.I)

INTEREST_SYNONYMS = {
    "waterfalls": ["waterfall", "waterfalls", "falls", "cascade", "cascades"],
    "mountains": ["mountain", "mountains", "hill", "hills", "highland"],
    "beaches": ["beach", "beaches", "coast", "coastal", "sea"],
    "culture": ["culture", "cultural", "temple", "heritage", "palace", "museum"],
    "nature": ["nature", "forest", "wildlife", "national park", "lake"],
    "quiet": ["quiet", "peaceful", "uncrowded", "calm"],
    "food": ["food", "cuisine", "thali"],
}


def _budget_inr(text: str) -> int | None:
    for m in _BUDGET.finditer(text):
        raw = m.group(1).replace(",", "")
        if not raw.isdigit():
            continue
        value = int(raw)
        if m.group(2):
            value *= 1000
        # Ignore bare small numbers that are more likely durations or party size.
        if value >= 1000:
            return value
    return None


def parse_intent(query: str, filters: dict[str, Any] | None = None, aliases: dict[str, str] | None = None) -> dict[str, Any]:
    """Form filters win over parsed text. `aliases` maps lowercase alias -> destination slug."""
    filters = filters or {}
    text = query or ""
    lowered = text.lower()
    interests: list[str] = []
    for key, words in INTEREST_SYNONYMS.items():
        if any(w in lowered for w in words):
            interests.append(key)

    days = filters.get("duration_days")
    if days is None:
        m = _DAYS_NUM.search(lowered)
        if m:
            days = int(m.group(1))
        else:
            for word, n in _DAYS_WORD.items():
                if re.search(rf"\b{word}\s+days?\b", lowered):
                    days = n
                    break

    travelers = filters.get("travelers")
    if travelers is None:
        m = _TRAVELERS.search(lowered)
        if m:
            travelers = int(m.group(1))

    origin = filters.get("origin")
    if not origin:
        m = _ORIGIN.search(text)
        origin = m.group(1).strip(" .") if m else None

    budget = filters.get("budget_inr")
    if budget is None:
        budget = _budget_inr(text)

    region = filters.get("region")
    destination_slug = filters.get("destination_slug")
    if not destination_slug and aliases:
        for alias, slug in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                destination_slug = slug
                break

    return {
        "interests": interests,
        "duration_days": days,
        "travelers": travelers,
        "origin": origin,
        "budget_inr": budget,
        "region": region,
        "destination_slug": destination_slug,
        "preferences": [i for i in interests if i in {"quiet"}],
    }


def redact_query(query: str, *, limit: int = 500) -> str:
    text = (query or "").strip()
    text = re.sub(r"[\w.+-]+@[\w.-]+", "[email]", text)
    text = re.sub(r"\b\d{12,19}\b", "[number]", text)
    return text[:limit]
