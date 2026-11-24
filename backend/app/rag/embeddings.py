"""Local embedding adapters.

Production never invents vectors. If no pinned local model is cached, dense search is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from app.config import get_settings
from app.rag.fusion import l2_normalize


class Embedder(Protocol):
    model_id: str
    revision: str
    dimension: int
    kind: str

    def encode(self, texts: list[str], *, is_query: bool) -> np.ndarray: ...


@dataclass
class SentenceTransformerEmbedder:
    model_id: str
    revision: str
    dimension: int
    kind: str
    _model: object

    def encode(self, texts: list[str], *, is_query: bool) -> np.ndarray:
        prepared = texts
        if is_query and "bge" in self.model_id.lower():
            prepared = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]
        vectors = self._model.encode(prepared, normalize_embeddings=True, convert_to_numpy=True)  # type: ignore[attr-defined]
        return np.asarray(vectors, dtype=np.float32)


@dataclass
class FastEmbedEmbedder:
    model_id: str
    revision: str
    dimension: int
    kind: str
    _model: object

    def encode(self, texts: list[str], *, is_query: bool) -> np.ndarray:
        prepared = texts
        if is_query and "bge" in self.model_id.lower():
            prepared = [f"Represent this sentence for searching relevant passages: {t}" for t in texts]
        rows = list(self._model.embed(prepared))  # type: ignore[attr-defined]
        return l2_normalize(np.asarray(rows, dtype=np.float32))


def get_embedder() -> Embedder | None:
    """Return a real local model, or None. Never returns a hash embedder."""
    settings = get_settings()
    cache = settings.knowledge_root / "models"
    cache.mkdir(parents=True, exist_ok=True)
    local_only = not settings.allow_model_download

    try:
        from fastembed import TextEmbedding

        model = TextEmbedding(
            settings.embedding_model,
            cache_dir=str(cache),
            local_files_only=local_only,
        )
        probe = next(model.embed(["dimension probe"]))
        return FastEmbedEmbedder(
            model_id=settings.embedding_model,
            revision=settings.embedding_model_revision or "unpinned",
            dimension=int(len(probe)),
            kind="fastembed",
            _model=model,
        )
    except Exception:
        pass

    try:
        from sentence_transformers import SentenceTransformer

        kwargs = {"cache_folder": str(cache)}
        if local_only:
            kwargs["local_files_only"] = True
        if settings.embedding_model_revision:
            kwargs["revision"] = settings.embedding_model_revision
        model = SentenceTransformer(settings.embedding_model, **kwargs)
        dim = int(model.get_sentence_embedding_dimension())
        return SentenceTransformerEmbedder(
            model_id=settings.embedding_model,
            revision=settings.embedding_model_revision or "unpinned",
            dimension=dim,
            kind="sentence_transformer",
            _model=model,
        )
    except Exception:
        return None


def rerank_scores(query: str, texts: list[str]) -> list[float] | None:
    """Cross-encoder logits, or None when the local model cannot be opened."""
    settings = get_settings()
    if not texts:
        return []
    try:
        from sentence_transformers import CrossEncoder

        kwargs = {"cache_folder": str(settings.knowledge_root / "models")}
        if not settings.allow_model_download:
            kwargs["local_files_only"] = True
        model = CrossEncoder(settings.rerank_model, **kwargs)
        pairs = [(query, text) for text in texts]
        scores = model.predict(pairs)
        return [float(s) for s in scores]
    except Exception:
        return None
