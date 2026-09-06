"""Typed records shared by the evaluator, adapter and reporters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceExpectation:
    relative_path: str
    section: str
    anchor: str
    authority: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SourceExpectation":
        return cls(
            relative_path=str(value.get("relative_path", "")),
            section=str(value.get("section", "")),
            anchor=str(value.get("anchor", "")),
            authority=str(value.get("authority", "")),
        )


@dataclass(frozen=True)
class EvaluationQuestion:
    id: str
    version: str
    split: str
    suite: str
    experiment_ids: tuple[str, ...]
    experiment_names: tuple[str, ...]
    category: str
    difficulty: str
    question: str
    answerable: bool
    expected_answer: str
    expected_points: tuple[str, ...]
    required_term_groups: tuple[tuple[str, ...], ...]
    forbidden_claims: tuple[str, ...]
    expected_source_tiers: tuple[str, ...]
    secondary_source_allowed: bool
    example_data_allowed: bool
    source: tuple[SourceExpectation, ...]
    relevant_experiment_ids: tuple[str, ...]
    top_k_hit_required: bool

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvaluationQuestion":
        retrieval = value["retrieval_expectation"]
        return cls(
            id=str(value["id"]),
            version=str(value["version"]),
            split=str(value["split"]),
            suite=str(value["suite"]),
            experiment_ids=tuple(str(item) for item in value["experiment_ids"]),
            experiment_names=tuple(str(item) for item in value["experiment_names"]),
            category=str(value["category"]),
            difficulty=str(value["difficulty"]),
            question=str(value["question"]),
            answerable=bool(value["answerable"]),
            expected_answer=str(value["expected_answer"]),
            expected_points=tuple(str(item) for item in value["expected_points"]),
            required_term_groups=tuple(
                tuple(str(term) for term in group)
                for group in value["required_term_groups"]
            ),
            forbidden_claims=tuple(str(item) for item in value["forbidden_claims"]),
            expected_source_tiers=tuple(
                str(item) for item in value["expected_source_tiers"]
            ),
            secondary_source_allowed=bool(value["secondary_source_allowed"]),
            example_data_allowed=bool(value["example_data_allowed"]),
            source=tuple(SourceExpectation.from_dict(item) for item in value["source"]),
            relevant_experiment_ids=tuple(
                str(item) for item in retrieval["relevant_experiment_ids"]
            ),
            top_k_hit_required=bool(retrieval["top_k_hit_required"]),
        )


@dataclass(frozen=True)
class RetrievedEvidence:
    rank: int
    experiment_id: str
    experiment_name: str
    source_file: str
    section: str
    chunk_id: str
    score: float
    text: str
    page_start: int | None = None
    page_end: int | None = None
    lexical_score: float = 0.0
    dense_score: float = 0.0
    evidence_id: str | None = None
    source_tier: str = "primary"
    source_kind: str = "formal_guide"
    authority: str = "course_official"
    is_example_data: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "RetrievedEvidence":
        return cls(
            rank=int(value.get("rank", 0)),
            experiment_id=str(value.get("experiment_id", "")),
            experiment_name=str(value.get("experiment_name", "")),
            source_file=str(value.get("source_file", value.get("source", ""))),
            section=str(value.get("section", "")),
            chunk_id=str(value.get("chunk_id", "")),
            score=float(value.get("score", 0.0) or 0.0),
            text=str(value.get("text", "")),
            page_start=_optional_int(value.get("page_start")),
            page_end=_optional_int(value.get("page_end")),
            lexical_score=float(value.get("lexical_score", 0.0) or 0.0),
            dense_score=float(value.get("dense_score", 0.0) or 0.0),
            evidence_id=(str(value["evidence_id"]) if value.get("evidence_id") else None),
            source_tier=str(value.get("source_tier", "primary")),
            source_kind=str(value.get("source_kind", "formal_guide")),
            authority=str(value.get("authority", "course_official")),
            is_example_data=bool(value.get("is_example_data", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ContextEvidence:
    """Evidence exposed to generation after context expansion.

    This is deliberately separate from ``RetrievedEvidence``: adjacent/parent
    chunks may be added while constructing the prompt even though they were not
    direct retrieval hits.
    """

    evidence_id: str
    experiment_id: str
    chunk_id: str
    source_file: str = ""
    section: str = ""
    context_relation: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ContextEvidence":
        return cls(
            evidence_id=str(value.get("evidence_id", value.get("id", ""))),
            experiment_id=str(value.get("experiment_id", "")),
            chunk_id=str(value.get("chunk_id", "")),
            source_file=str(value.get("source_file", value.get("source", ""))),
            section=str(value.get("section", "")),
            context_relation=(
                str(value["context_relation"])
                if value.get("context_relation") else None
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Prediction:
    id: str
    mode: str
    answer: str
    retrieved_evidence: list[RetrievedEvidence]
    citations: list[str]
    grounded: bool
    warnings: list[str] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)
    error: str | None = None
    context_evidence: list[ContextEvidence] = field(default_factory=list)
    model_citations: list[str] | None = None
    citation_contract_version: str = "2"

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Prediction":
        return cls(
            id=str(value.get("id", "")),
            mode=str(value.get("mode", "blind")),
            answer=str(value.get("answer", "")),
            retrieved_evidence=[
                RetrievedEvidence.from_dict(item)
                for item in value.get("retrieved_evidence", [])
                if isinstance(item, dict)
            ],
            citations=[str(item) for item in value.get("citations", [])],
            grounded=bool(value.get("grounded", False)),
            warnings=[str(item) for item in value.get("warnings", [])],
            timings_ms={
                str(key): float(item) for key, item in value.get("timings_ms", {}).items()
            },
            error=(str(value["error"]) if value.get("error") else None),
            context_evidence=[
                ContextEvidence.from_dict(item)
                for item in value.get("context_evidence", [])
                if isinstance(item, dict)
            ],
            model_citations=(
                [str(item) for item in value.get("model_citations", [])]
                if value.get("model_citations") is not None else None
            ),
            citation_contract_version=str(value.get("citation_contract_version", "1")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "answer": self.answer,
            "retrieved_evidence": [item.to_dict() for item in self.retrieved_evidence],
            "citations": list(self.citations),
            "grounded": self.grounded,
            "warnings": list(self.warnings),
            "timings_ms": dict(self.timings_ms),
            "error": self.error,
            "context_evidence": [item.to_dict() for item in self.context_evidence],
            "model_citations": (
                list(self.model_citations) if self.model_citations is not None else None
            ),
            "citation_contract_version": self.citation_contract_version,
        }


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)
