"""Bounded entity walk. Separate from the LangGraph execution graph."""

from __future__ import annotations

from collections import deque


def bfs_evidence(
    *,
    seed_entity_ids: list[str],
    edges: list[dict],
    max_hops: int = 2,
) -> list[dict]:
    """edges: subject_id, object_id, evidence_chunk_id, predicate, method."""
    adjacency: dict[str, list[dict]] = {}
    for edge in edges:
        adjacency.setdefault(edge["subject_id"], []).append(edge)
        adjacency.setdefault(edge["object_id"], []).append(edge)
    seen = set(seed_entity_ids)
    queue: deque[tuple[str, int]] = deque((sid, 0) for sid in seed_entity_ids)
    ordered: list[dict] = []
    while queue:
        node, hop = queue.popleft()
        if hop >= max_hops:
            continue
        for edge in adjacency.get(node, []):
            other = edge["object_id"] if edge["subject_id"] == node else edge["subject_id"]
            if other in seen:
                continue
            seen.add(other)
            ordered.append({**edge, "hop": hop + 1, "via": node})
            queue.append((other, hop + 1))
    return ordered
