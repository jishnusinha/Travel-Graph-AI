"""Conservative attraction-name keys. This folds case, punctuation, a leading "the", and a trailing plural."""

from __future__ import annotations

import re
import unicodedata


def name_key(name: str) -> str:
    text = unicodedata.normalize("NFKC", name or "").casefold()
    text = text.replace("'", "").replace("’", "")
    text = re.sub(r"[^0-9a-z\u00c0-\uffff]+", " ", text)
    words: list[str] = []
    for word in text.split():
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        words.append(word)
    if words and words[0] == "the":
        words = words[1:]
    return " ".join(words)


def dedupe_named(rows: list[dict]) -> list[dict]:
    """Merge rows that share a name key. Coordinates from a located row fill an unlocated one."""
    kept: list[dict] = []
    index: dict[str, dict] = {}
    for row in rows:
        name = str(row.get("name") or "").strip()
        key = name_key(name)
        if not key:
            continue
        current = index.get(key)
        if current is None:
            item = dict(row)
            item["name"] = name
            item["aliases"] = list(row.get("aliases") or [])
            index[key] = item
            kept.append(item)
            continue
        if name != current["name"] and name not in current["aliases"]:
            current["aliases"].append(name)
        if current.get("lat") is None and row.get("lat") is not None:
            current["lat"] = row.get("lat")
            current["lon"] = row.get("lon")
            current["coordinate_status"] = row.get("coordinate_status") or current.get("coordinate_status")
            current["osm_type"] = row.get("osm_type")
            current["osm_id"] = row.get("osm_id")
            current["geometry_kind"] = row.get("geometry_kind") or current.get("geometry_kind")
        refs = list(current.get("source_refs") or [])
        for ref in row.get("source_refs") or []:
            if ref not in refs:
                refs.append(ref)
        current["source_refs"] = refs
    return kept
