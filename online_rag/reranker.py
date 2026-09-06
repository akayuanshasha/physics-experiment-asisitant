"""Optional local cross-encoder reranking without implicit model downloads."""

from __future__ import annotations

from typing import Any, Protocol

from .models import RetrievalHit


class Reranker(Protocol):
    model_name: str

    def rerank(
        self, query: str, hits: list[RetrievalHit], *, top_k: int
    ) -> list[RetrievalHit]: ...


class CrossEncoderReranker:
    """sentence-transformers CrossEncoder adapter.

    A model object can be injected for tests. Production construction is explicit:
    callers must provide ``RERANKER_MODEL`` so importing this module never downloads
    a model unexpectedly.
    """

    def __init__(self, model_name: str, *, model: Any | None = None):
        if not str(model_name or "").strip():
            raise ValueError("CrossEncoderReranker 需要非空 model_name")
        self.model_name = str(model_name).strip()
        if model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError(
                    "已配置 RERANKER_MODEL，但未安装 sentence-transformers"
                ) from exc
            model = CrossEncoder(self.model_name)
        self.model = model

    def rerank(
        self, query: str, hits: list[RetrievalHit], *, top_k: int
    ) -> list[RetrievalHit]:
        if not hits or top_k <= 0:
            return []
        pairs = [(query, hit.chunk.embedding_text()) for hit in hits]
        raw_scores = self.model.predict(pairs)
        scores = [float(value) for value in raw_scores]
        if len(scores) != len(hits):
            raise ValueError("Cross-encoder 返回的分数数量与候选数不一致")
        for hit, score in zip(hits, scores):
            hit.rerank_score = score
        return sorted(
            hits,
            key=lambda hit: (
                -(hit.rerank_score if hit.rerank_score is not None else float("-inf")),
                -hit.score,
                hit.chunk.chunk_id,
            ),
        )[:top_k]
