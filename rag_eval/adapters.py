"""Adapter from the benchmark model to the real online_rag assistant."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from online_rag import (
    AssistantConfig,
    HybridRetriever,
    PhysicsExperimentAssistant,
    RetrievalConfig,
    create_assistant_from_env,
)

from .models import ContextEvidence, EvaluationQuestion, Prediction, RetrievedEvidence


@dataclass
class AdapterResult:
    prediction: Prediction
    raw: dict[str, Any]


class OnlineRagAdapter:
    """Evaluate only the intended replacement RAG; no legacy comparison path."""

    def __init__(self, assistant: PhysicsExperimentAssistant):
        self.assistant = assistant

    @classmethod
    def from_env(cls) -> "OnlineRagAdapter":
        return cls(create_assistant_from_env())

    @classmethod
    def lexical_only(cls) -> "OnlineRagAdapter":
        class DisabledDenseBackend:
            model_name = "disabled-for-lexical-diagnostic"

            @staticmethod
            def embed_documents(texts: list[str]) -> list[list[float]]:
                return [[1.0] for _ in texts]

            @staticmethod
            def embed_queries(texts: list[str]) -> list[list[float]]:
                return [[1.0] for _ in texts]

        class DisabledChatBackend:
            model_name = "disabled-for-retrieval-only"

            @staticmethod
            def complete(*args, **kwargs):
                raise RuntimeError("lexical-only 模式不能调用生成模型")

        config = RetrievalConfig(
            cache_path=".cache/online_rag/lexical_only_vectors.json",
            dense_score_threshold=1.1,
            dense_weight=0.0,
        )
        retriever = HybridRetriever.from_corpus(DisabledDenseBackend(), config)
        assistant = PhysicsExperimentAssistant(
            retriever, DisabledChatBackend(), AssistantConfig()
        )
        return cls(assistant)

    def predict(self, question: EvaluationQuestion, *, mode: str = "blind") -> AdapterResult:
        if mode not in {"blind", "page-context"}:
            raise ValueError("mode 必须是 blind 或 page-context")
        page_context = question.experiment_ids if mode == "page-context" else None
        started = time.perf_counter()
        try:
            result = self.assistant.ask(question.question, experiment_ids=page_context)
            evidence_ids = {
                item.chunk.chunk_id: item.evidence_id for item in result.evidence
            }
            retrieved = [
                RetrievedEvidence(
                    rank=rank,
                    experiment_id=hit.chunk.experiment_id,
                    experiment_name=hit.chunk.experiment_name,
                    source_file=hit.chunk.source,
                    section=hit.chunk.section,
                    chunk_id=hit.chunk.chunk_id,
                    score=hit.score,
                    text=hit.chunk.text,
                    page_start=hit.chunk.page_start,
                    page_end=hit.chunk.page_end,
                    lexical_score=hit.lexical_score,
                    dense_score=hit.dense_score,
                    evidence_id=evidence_ids.get(hit.chunk.chunk_id),
                    source_tier=hit.chunk.source_tier,
                    source_kind=hit.chunk.source_kind,
                    authority=hit.chunk.authority,
                    is_example_data=hit.chunk.is_example_data,
                )
                for rank, hit in enumerate(result.retrieval.hits, 1)
            ]
            prediction = Prediction(
                id=question.id,
                mode=mode,
                answer=result.answer,
                retrieved_evidence=retrieved,
                citations=[item.evidence_id for item in result.citations],
                grounded=result.grounded,
                warnings=list(result.warnings),
                timings_ms=dict(result.timings_ms),
                context_evidence=[
                    ContextEvidence(
                        evidence_id=item.evidence_id,
                        experiment_id=item.chunk.experiment_id,
                        chunk_id=item.chunk.chunk_id,
                        source_file=item.chunk.source,
                        section=item.chunk.section,
                        context_relation=item.context_relation,
                    )
                    for item in result.evidence
                ],
                # The online answer object intentionally hides inline [E#]
                # markers. Do not mislabel attached context as model citations.
                model_citations=None,
            )
            return AdapterResult(prediction=prediction, raw=result.to_dict())
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            return AdapterResult(
                prediction=Prediction(
                    id=question.id,
                    mode=mode,
                    answer="",
                    retrieved_evidence=[],
                    citations=[],
                    grounded=False,
                    timings_ms={"total": (time.perf_counter() - started) * 1000},
                    error=error,
                ),
                raw={"error": error},
            )

    def retrieve_only(
        self, question: EvaluationQuestion, *, mode: str = "blind", top_k: int = 12,
    ) -> AdapterResult:
        if mode not in {"blind", "page-context"}:
            raise ValueError("mode 必须是 blind 或 page-context")
        page_context = question.experiment_ids if mode == "page-context" else None
        started = time.perf_counter()
        try:
            if page_context:
                result = self.assistant.retriever.retrieve(
                    question.question, top_k=top_k, experiment_ids=page_context
                )
            else:
                result = self.assistant.retriever.retrieve(question.question, top_k=top_k)
            retrieved = [
                RetrievedEvidence(
                    rank=rank,
                    experiment_id=hit.chunk.experiment_id,
                    experiment_name=hit.chunk.experiment_name,
                    source_file=hit.chunk.source,
                    section=hit.chunk.section,
                    chunk_id=hit.chunk.chunk_id,
                    score=hit.score,
                    text=hit.chunk.text,
                    page_start=hit.chunk.page_start,
                    page_end=hit.chunk.page_end,
                    lexical_score=hit.lexical_score,
                    dense_score=hit.dense_score,
                    source_tier=hit.chunk.source_tier,
                    source_kind=hit.chunk.source_kind,
                    authority=hit.chunk.authority,
                    is_example_data=hit.chunk.is_example_data,
                )
                for rank, hit in enumerate(result.hits, 1)
            ]
            prediction = Prediction(
                id=question.id,
                mode=mode,
                answer="",
                retrieved_evidence=retrieved,
                citations=[],
                grounded=False,
                warnings=list(result.warnings),
                timings_ms=dict(result.timings_ms),
            )
            return AdapterResult(prediction=prediction, raw=result.to_dict())
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            return AdapterResult(
                prediction=Prediction(
                    id=question.id,
                    mode=mode,
                    answer="",
                    retrieved_evidence=[],
                    citations=[],
                    grounded=False,
                    timings_ms={"total": (time.perf_counter() - started) * 1000},
                    error=error,
                ),
                raw={"error": error},
            )
