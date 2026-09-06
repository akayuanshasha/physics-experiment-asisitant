from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from online_rag.benchmark import (
    BenchmarkQueryEmbeddingBackend,
    build_benchmark_query_variants,
    build_corpus_snapshot,
    compare_reports,
    evaluate_hybrid_retriever,
)
from online_rag.evaluation import EvaluationCase
from online_rag.models import Chunk, RetrievalHit, RetrievalResult
from online_rag.retriever import RetrievalConfig


def chunk(chunk_id: str, experiment_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id, text, experiment_id, experiment_id,
        f"{experiment_id}.pdf", "实验原理", 1, 1,
    )


class FakeRetriever:
    def __init__(self, results: dict[str, list[Chunk]]):
        self.results = results

    def retrieve(self, question: str, top_k: int = 6) -> RetrievalResult:
        hits = [RetrievalHit(item, 1.0 / rank, 2.0, 0.8)
                for rank, item in enumerate(self.results[question], start=1)]
        return RetrievalResult(
            question, question, [question], hits[:top_k],
            timings_ms={"total": 12.5},
        )


class FakeEmbeddingBackend:
    model_name = "fake-embedding"

    def __init__(self):
        self.query_calls = 0

    def embed_documents(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def embed_queries(self, texts):
        self.query_calls += 1
        return [[float(len(text)), 1.0] for text in texts]


class QueryEmbeddingCacheTest(unittest.TestCase):
    def test_benchmark_prewarm_uses_online_uncertainty_expansion(self):
        variants = build_benchmark_query_variants(
            "不确定度怎么计算", RetrievalConfig(max_query_variants=8),
        )
        self.assertIn("A类标准不确定度", variants)
        self.assertIn("B类标准不确定度", variants)
        self.assertIn("合成标准不确定度", variants)

    def test_query_vectors_are_persisted_and_reused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "queries.json"
            first_backend = FakeEmbeddingBackend()
            first = BenchmarkQueryEmbeddingBackend(first_backend, path)
            stats = first.prewarm(["问题一", "问题二", "问题一"], batch_size=1, batch_delay_seconds=0)
            self.assertEqual(stats["embedded"], 2)
            self.assertEqual(first_backend.query_calls, 2)

            second_backend = FakeEmbeddingBackend()
            second = BenchmarkQueryEmbeddingBackend(second_backend, path)
            vectors = second.embed_queries(["问题一", "问题二"])
            self.assertEqual(second_backend.query_calls, 0)
            self.assertEqual(len(vectors), 2)


class CorpusSnapshotTest(unittest.TestCase):
    def test_snapshot_is_order_independent_and_content_sensitive(self):
        first = chunk("a", "exp1", "原始内容")
        second = chunk("b", "exp2", "另一内容")
        left = build_corpus_snapshot([first, second])
        right = build_corpus_snapshot([second, first])
        changed = build_corpus_snapshot([
            chunk("a2", "exp1", "修改内容"), second,
        ])
        self.assertEqual(left["fingerprint"], right["fingerprint"])
        self.assertNotEqual(left["fingerprint"], changed["fingerprint"])
        self.assertNotEqual(
            left["experiment_fingerprints"]["exp1"],
            changed["experiment_fingerprints"]["exp1"],
        )
        self.assertEqual(
            left["experiment_fingerprints"]["exp2"],
            changed["experiment_fingerprints"]["exp2"],
        )

    def test_cross_experiment_exact_duplicates_are_reported_without_text(self):
        snapshot = build_corpus_snapshot([
            chunk("a", "exp1", "完全相同的正文"),
            chunk("b", "exp2", "完全相同的正文"),
        ])
        self.assertEqual(snapshot["cross_experiment_exact_duplicate_groups"], 1)
        duplicate = snapshot["cross_experiment_exact_duplicates"][0]
        self.assertEqual(duplicate["experiment_ids"], ["exp1", "exp2"])
        self.assertNotIn("text", duplicate)


class DetailedEvaluationTest(unittest.TestCase):
    def test_chunk_and_unique_experiment_metrics_are_both_recorded(self):
        exp1a = chunk("a", "exp1", "内容一")
        exp1b = chunk("b", "exp1", "内容二")
        exp2 = chunk("c", "exp2", "内容三")
        cases = [
            EvaluationCase("q1", ("exp1",)),
            EvaluationCase("q2", ("exp2",)),
        ]
        metrics, details = evaluate_hybrid_retriever(
            FakeRetriever({"q1": [exp1a], "q2": [exp1a, exp1b, exp2]}),
            cases, top_k=3,
        )
        self.assertEqual(metrics["chunk_recall_at_1"], 0.5)
        self.assertEqual(metrics["chunk_recall_at_3"], 1.0)
        self.assertEqual(details[1]["chunk_rank"], 3)
        self.assertEqual(details[1]["experiment_rank"], 2)


class ComparisonTest(unittest.TestCase):
    @staticmethod
    def _report(rank: int | None, fingerprint: str, exp_hash: str) -> dict:
        return {
            "schema_version": 1,
            "evaluation_set": {"sha256": "cases"},
            "embedding": {"model": "embedding"},
            "retrieval_config": {"candidate_k": 20},
            "corpus": {
                "fingerprint": fingerprint,
                "chunks": 10,
                "characters": 100,
                "experiment_fingerprints": {"exp1": exp_hash},
            },
            "metrics": {"cases": 1, "top_k": 5, "chunk_recall_at_5": 1.0},
            "cases": [{
                "case_id": "R001", "query": "问题",
                "chunk_rank": rank, "experiment_rank": rank,
            }],
        }

    def test_comparison_identifies_changed_experiment_and_rank_improvement(self):
        comparison = compare_reports(
            self._report(3, "old", "old-exp"),
            self._report(1, "new", "new-exp"),
        )
        self.assertTrue(comparison["strictly_comparable"])
        self.assertEqual(comparison["corpus_change"]["changed_experiments"], ["exp1"])
        self.assertEqual(comparison["improved_cases"], 1)
        self.assertEqual(comparison["regressed_cases"], 0)


if __name__ == "__main__":
    unittest.main()
