"""Small deterministic retrieval evaluation harness (no LLM judge)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import RetrievalResult


@dataclass(frozen=True)
class EvaluationCase:
    query: str
    expected_experiments: tuple[str, ...]


class RetrieverLike(Protocol):
    def retrieve(self, question: str, top_k: int = 6) -> RetrievalResult: ...


def load_evaluation_cases(path: str | Path) -> list[EvaluationCase]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [EvaluationCase(
        query=str(row["query"]),
        expected_experiments=tuple(str(x) for x in row["expected_experiments"]),
    ) for row in rows]


def evaluate_retriever(
    retriever: RetrieverLike, cases: list[EvaluationCase], *, top_k: int = 5,
) -> dict:
    reciprocal_ranks: list[float] = []
    details: list[dict] = []
    for case in cases:
        result = retriever.retrieve(case.query, top_k=top_k)
        ranked = [hit.chunk.experiment_id for hit in result.hits]
        rank = next(
            (index for index, experiment_id in enumerate(ranked, start=1)
             if experiment_id in case.expected_experiments),
            None,
        )
        reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        details.append({
            "query": case.query,
            "expected_experiments": list(case.expected_experiments),
            "rank": rank,
            "returned_experiments": ranked,
        })
    count = len(cases)
    return {
        "cases": count,
        f"recall_at_{top_k}": (
            sum(value > 0 for value in reciprocal_ranks) / count if count else 0.0
        ),
        "mrr": sum(reciprocal_ranks) / count if count else 0.0,
        "details": details,
    }
