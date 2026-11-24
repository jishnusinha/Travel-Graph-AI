from __future__ import annotations

import hashlib

import numpy as np

from app.rag.fusion import l2_normalize


class TestEmbedder:
    """Bag-of-tokens test double. Production get_embedder() never returns this."""

    model_id = "test-double-v1"
    revision = "test"
    dimension = 32
    kind = "test_double"

    def encode(self, texts: list[str], *, is_query: bool) -> np.ndarray:
        del is_query
        rows = []
        for text in texts:
            vec = np.zeros(self.dimension, dtype=np.float32)
            for token in text.lower().split():
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                vec[digest[0] % self.dimension] += 1.0
            rows.append(vec)
        return l2_normalize(np.vstack(rows))
