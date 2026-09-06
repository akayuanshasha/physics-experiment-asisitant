"""Public data models returned by the independent retrieval core."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    experiment_id: str
    experiment_name: str
    source: str
    section: str
    page_start: int | None = None
    page_end: int | None = None
    parent_id: str | None = None
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None
    source_tier: str = "primary"
    source_kind: str = "formal_guide"
    authority: str = "course_official"
    is_example_data: bool = False

    def embedding_text(self) -> str:
        return f"实验：{self.experiment_name}\n章节：{self.section}\n{self.text}"


@dataclass
class RetrievalHit:
    chunk: Chunk
    score: float
    lexical_score: float = 0.0
    dense_score: float = 0.0
    rerank_score: float | None = None
    context_relation: str | None = None
    matched_variants: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self.chunk)
        data.update(
            score=self.score,
            lexical_score=self.lexical_score,
            dense_score=self.dense_score,
            rerank_score=self.rerank_score,
            context_relation=self.context_relation,
            matched_variants=list(self.matched_variants),
        )
        return data


@dataclass
class RetrievalResult:
    query: str
    normalized_query: str
    query_variants: list[str]
    hits: list[RetrievalHit]
    retrieval_mode: str = "hybrid"
    warnings: list[str] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)
    authority_mode: str = ""
    example_data_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "normalized_query": self.normalized_query,
            "query_variants": list(self.query_variants),
            "hits": [hit.to_dict() for hit in self.hits],
            "retrieval_mode": self.retrieval_mode,
            "warnings": list(self.warnings),
            "timings_ms": dict(self.timings_ms),
            "authority_mode": self.authority_mode,
            "example_data_enabled": self.example_data_enabled,
        }
