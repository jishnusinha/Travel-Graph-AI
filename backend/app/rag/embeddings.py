"""Local embedding and cross-encoder adapters.

Production never invents vectors. If the pinned local model is not cached, dense
search and reranking stay unavailable and the retrieval trace says so.
"""

from __future__ import annotations

import hashlib
import inspect
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from app.config import get_settings
from app.rag.fusion import l2_normalize

logger = logging.getLogger(__name__)

# ONNX build of the same MiniLM cross-encoder. Used when PyTorch is not installed.
_FASTEMBED_RERANK = {
    "cross-encoder/ms-marco-MiniLM-L-6-v2": "Xenova/ms-marco-MiniLM-L-6-v2",
}

_lock = threading.Lock()
_embedder: Embedder | None = None
_embedder_key: tuple | None = None
_embedder_failed: set[tuple] = set()
_reranker: Any = None
_reranker_key: tuple | None = None
_reranker_failed: set[tuple] = set()
_rerank_model_id = ""
_rerank_kind = ""


class Embedder(Protocol):
    model_id: str
    revision: str
    dimension: int
    kind: str

    def encode(self, texts: list[str], *, is_query: bool) -> np.ndarray: ...


def clear_model_cache() -> None:
    global _embedder, _embedder_key, _reranker, _reranker_key, _rerank_model_id, _rerank_kind
    with _lock:
        _embedder = None
        _embedder_key = None
        _embedder_failed.clear()
        _reranker = None
        _reranker_key = None
        _reranker_failed.clear()
        _rerank_model_id = ""
        _rerank_kind = ""


def rerank_model_id() -> str:
    return _rerank_model_id


def rerank_kind() -> str:
    return _rerank_kind


def _file_revision(cache: Path, model_id: str) -> str:
    slug = model_id.split("/")[-1].lower()
    files = [path for path in cache.rglob("*") if path.is_file() and path.suffix.lower() in {".onnx", ".bin", ".safetensors"}]
    if not files:
        return "unpinned"
    ranked = sorted(files, key=lambda path: (slug not in str(path).lower(), str(path)))
    digest = hashlib.sha256()
    with ranked[0].open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()[:16]


def _accepted(signature: inspect.Signature, name: str) -> bool:
    return name in signature.parameters or any(p.kind is inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values())


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
            prepared = [f"Represent this sentence for searching relevant passages: {text}" for text in texts]
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
        parts: list[np.ndarray] = []
        for start in range(0, len(texts), 64):
            batch = texts[start : start + 64]
            if is_query and hasattr(self._model, "query_embed"):
                rows = list(self._model.query_embed(batch))  # type: ignore[attr-defined]
            else:
                prepared = batch
                if is_query and "bge" in self.model_id.lower():
                    prepared = [f"Represent this sentence for searching relevant passages: {text}" for text in batch]
                rows = list(self._model.embed(prepared))  # type: ignore[attr-defined]
            parts.append(l2_normalize(np.asarray(rows, dtype=np.float32)))
        if not parts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        return np.vstack(parts)


def load_embedder(*, local_only: bool | None = None) -> Embedder | None:
    """Open the configured local embedding model. Does not return a hash embedder."""
    global _embedder, _embedder_key
    settings = get_settings()
    cache = settings.knowledge_root / "models"
    cache.mkdir(parents=True, exist_ok=True)
    offline = not settings.allow_model_download if local_only is None else local_only
    key = (settings.embedding_model, settings.embedding_model_revision, offline, str(cache))
    with _lock:
        if _embedder is not None and _embedder_key == key:
            return _embedder
        if key in _embedder_failed:
            return None
    opened = _open_embedder(settings.embedding_model, settings.embedding_model_revision, cache, offline)
    with _lock:
        if opened is None:
            _embedder_failed.add(key)
            return None
        _embedder = opened
        _embedder_key = key
        _embedder_failed.discard(key)
        return _embedder


def get_embedder() -> Embedder | None:
    return load_embedder()


def _open_embedder(model_id: str, revision: str, cache: Path, local_only: bool) -> Embedder | None:
    fast = _open_fastembed(model_id, revision, cache, local_only)
    if fast is not None:
        return fast
    return _open_sentence_transformer(model_id, revision, cache, local_only)


def _open_fastembed(model_id: str, revision: str, cache: Path, local_only: bool) -> Embedder | None:
    try:
        from fastembed import TextEmbedding
    except Exception as exc:
        logger.info("fastembed is not importable: %s", exc)
        return None
    try:
        kwargs: dict[str, Any] = {}
        signature = inspect.signature(TextEmbedding.__init__)
        if _accepted(signature, "cache_dir"):
            kwargs["cache_dir"] = str(cache)
        if _accepted(signature, "local_files_only"):
            kwargs["local_files_only"] = local_only
        model = TextEmbedding(model_id, **kwargs)
        probe = next(iter(model.embed(["dimension probe"])))
        return FastEmbedEmbedder(
            model_id=model_id,
            revision=revision or _file_revision(cache, model_id),
            dimension=int(len(probe)),
            kind="fastembed",
            _model=model,
        )
    except Exception as exc:
        logger.warning("Embedding model %s could not be opened with fastembed: %s", model_id, exc)
        return None


def _open_sentence_transformer(model_id: str, revision: str, cache: Path, local_only: bool) -> Embedder | None:
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as exc:
        logger.info("sentence-transformers is not importable: %s", exc)
        return None
    try:
        kwargs: dict[str, Any] = {"cache_folder": str(cache)}
        if local_only:
            kwargs["local_files_only"] = True
        if revision:
            kwargs["revision"] = revision
        model = SentenceTransformer(model_id, **kwargs)
        dim = int(model.get_sentence_embedding_dimension())
        return SentenceTransformerEmbedder(
            model_id=model_id,
            revision=revision or _file_revision(cache, model_id),
            dimension=dim,
            kind="sentence_transformer",
            _model=model,
        )
    except Exception as exc:
        logger.warning("Embedding model %s could not be opened with sentence-transformers: %s", model_id, exc)
        return None


def _score_list(raw: Any) -> list[float]:
    scores: list[float] = []
    for item in raw:
        if hasattr(item, "score"):
            scores.append(float(item.score))
        else:
            scores.append(float(item))
    return scores


def load_reranker(*, local_only: bool | None = None) -> Any:
    global _reranker, _reranker_key, _rerank_model_id, _rerank_kind
    settings = get_settings()
    cache = settings.knowledge_root / "models"
    cache.mkdir(parents=True, exist_ok=True)
    offline = not settings.allow_model_download if local_only is None else local_only
    key = (settings.rerank_model, offline, str(cache))
    with _lock:
        if _reranker is not None and _reranker_key == key:
            return _reranker
        if key in _reranker_failed:
            return None
    opened, model_id, kind = _open_reranker(settings.rerank_model, cache, offline)
    with _lock:
        if opened is None:
            _reranker_failed.add(key)
            return None
        _reranker = opened
        _reranker_key = key
        _rerank_model_id = model_id
        _rerank_kind = kind
        _reranker_failed.discard(key)
        return _reranker


def _open_reranker(configured: str, cache: Path, local_only: bool) -> tuple[Any, str, str] | tuple[None, str, str]:
    try:
        from sentence_transformers import CrossEncoder

        kwargs: dict[str, Any] = {"cache_folder": str(cache)}
        if local_only:
            kwargs["local_files_only"] = True
        model = CrossEncoder(configured, **kwargs)
        return model, configured, "sentence_transformer_cross_encoder"
    except Exception as exc:
        logger.info("sentence-transformers cross-encoder unavailable: %s", exc)
    onnx_name = _FASTEMBED_RERANK.get(configured, configured)
    try:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
    except Exception as exc:
        logger.warning("No cross-encoder backend is installed: %s", exc)
        return None, "", ""
    try:
        kwargs = {}
        signature = inspect.signature(TextCrossEncoder.__init__)
        if _accepted(signature, "cache_dir"):
            kwargs["cache_dir"] = str(cache)
        if _accepted(signature, "local_files_only"):
            kwargs["local_files_only"] = local_only
        if _accepted(signature, "model_name"):
            model = TextCrossEncoder(model_name=onnx_name, **kwargs)
        else:
            model = TextCrossEncoder(onnx_name, **kwargs)
        return model, onnx_name, "fastembed_cross_encoder"
    except Exception as exc:
        logger.warning("Cross-encoder %s could not be opened: %s", onnx_name, exc)
        return None, "", ""


def rerank_scores(query: str, texts: list[str]) -> list[float] | None:
    """Cross-encoder scores, or None when the local model cannot be opened."""
    if not texts:
        return []
    model = load_reranker()
    if model is None:
        return None
    try:
        if hasattr(model, "rerank"):
            return _score_list(model.rerank(query, texts))
        pairs = [(query, text) for text in texts]
        return _score_list(model.predict(pairs))
    except Exception as exc:
        logger.warning("Cross-encoder scoring failed: %s", exc)
        return None
