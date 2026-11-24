"""Reciprocal rank fusion and cosine helpers. Scores are not comparable across stages."""

from __future__ import annotations

import numpy as np


def rrf_fuse(rank_lists: list[list[str]], *, k: int = 60) -> list[tuple[str, float]]:
    """rank lists are best-first. Ties break by chunk id ascending."""
    scores: dict[str, float] = {}
    for ranks in rank_lists:
        for index, chunk_id in enumerate(ranks, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + index)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def cosine_scores(matrix: np.ndarray, query: np.ndarray) -> np.ndarray:
    """Both inputs must already be L2-normalized. Result is exact dot product."""
    if matrix.size == 0:
        return np.zeros((0,), dtype=np.float32)
    q = query.astype(np.float32, copy=False)
    return matrix @ q


def l2_normalize(vectors: np.ndarray) -> np.ndarray:
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms
