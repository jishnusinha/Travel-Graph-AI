"""Extractive answers. This is not an LLM. Claims are sentences copied from evidence."""

from __future__ import annotations

import re

from app.rag.textutil import significant_terms


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if len(p.strip()) > 40]


def compose_answer(query: str, evidence: list[dict], *, min_overlap: int = 1) -> dict:
    terms = significant_terms(query)
    claims: list[dict] = []
    used: set[str] = set()
    for item in evidence:
        excerpt = item.get("text") or ""
        for sentence in _sentences(excerpt):
            overlap = significant_terms(sentence) & terms
            if len(overlap) < min_overlap:
                continue
            key = sentence[:180]
            if key in used:
                continue
            used.add(key)
            claims.append(
                {
                    "text": sentence,
                    "evidence_ids": [item["citation_id"]] if item.get("citation_id") else [],
                    "chunk_id": item.get("chunk_id"),
                    "overlap_terms": sorted(overlap),
                }
            )
            if len(claims) >= 4:
                break
        if len(claims) >= 4:
            break
    insufficient = len(claims) == 0
    return {
        "claims": claims,
        "unknowns": [] if claims else ["No retrieved sentence supports this question."],
        "insufficient_evidence": insufficient,
        "generation_mode": "deterministic_evidence",
    }


def validate_llm_claims(claims: list[dict], evidence_by_id: dict[str, dict]) -> tuple[list[dict], list[str]]:
    """Drop claims whose citation is outside the selected evidence or shares no terms with it."""
    kept: list[dict] = []
    rejected: list[str] = []
    for claim in claims:
        ids = [str(i) for i in claim.get("evidence_ids") or []]
        if not ids or any(i not in evidence_by_id for i in ids):
            rejected.append("citation_not_in_selected_evidence")
            continue
        blob = " ".join(evidence_by_id[i].get("text") or "" for i in ids)
        if not (significant_terms(claim.get("text") or "") & significant_terms(blob)):
            rejected.append("claim_not_supported_by_excerpt")
            continue
        kept.append(claim)
    return kept, rejected
