from __future__ import annotations

import unittest

from online_rag.models import Chunk
from rag_eval.corpus_audit import audit_corpus
from rag_eval.dataset import DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH, load_questions
from rag_eval.models import ContextEvidence, Prediction, RetrievedEvidence
from rag_eval.scoring import build_report, normalized, score_prediction
from rag_eval.regression import evaluate_regression_gate
from rag_eval.cli import DEFAULT_THRESHOLDS_PATH, _retrieval_runtime_summary


class DatasetTest(unittest.TestCase):
    def test_frozen_dataset_has_expected_split(self):
        questions = load_questions(DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH)
        self.assertEqual(len(questions), 71)
        self.assertEqual(sum(item.split == "dev" for item in questions), 56)
        self.assertEqual(sum(item.split == "test" for item in questions), 15)
        self.assertTrue(all(item.expected_source_tiers for item in questions))

    def test_regression_gate_blocks_recall_drop(self):
        summary = {
            "recall_at_1": 0.5, "recall_at_3": 1.0, "recall_at_5": 1.0,
            "source_metadata_complete_rate_at_5": 1.0,
            "prediction_errors": 0, "latency_ms": {"p95": 10.0},
        }
        gate = evaluate_regression_gate(
            summary, DEFAULT_THRESHOLDS_PATH, "lexical_retrieval",
        )
        self.assertFalse(gate["passed"])
        self.assertIn("recall_at_1", [
            item["metric"] for item in gate["checks"] if not item["passed"]
        ])

    def test_hybrid_gate_blocks_complete_bm25_fallback(self):
        summary = {
            "recall_at_1": 1.0, "recall_at_3": 1.0, "recall_at_5": 1.0,
            "source_metadata_complete_rate_at_5": 1.0,
            "expected_source_tier_rate_at_5": 1.0,
            "secondary_source_leak_rate_at_5": 0.0,
            "example_data_misuse_count": 0,
            "prediction_errors": 0,
            "latency_ms": {"p95": 10.0},
            "retrieval_runtime": {
                "hybrid_query_rate": 0.0,
                "bm25_fallback_rate": 1.0,
                "unknown_mode_rate": 0.0,
                "dense_nonzero_hit_count": 0,
                "document_vector_coverage": 0.0,
            },
        }
        gate = evaluate_regression_gate(
            summary, DEFAULT_THRESHOLDS_PATH, "hybrid_retrieval",
        )
        self.assertFalse(gate["passed"])
        self.assertIn("retrieval_runtime.hybrid_query_rate", [
            item["metric"] for item in gate["checks"] if not item["passed"]
        ])

    def test_runtime_summary_records_real_hybrid_use(self):
        class Retriever:
            dense_available = True
            chunks = [object(), object()]
            document_vectors = [[1.0], [1.0]]

        summary = _retrieval_runtime_summary([{
            "response": {
                "retrieval_mode": "hybrid",
                "hits": [{"dense_score": 0.8}, {"dense_score": 0.0}],
            },
        }], Retriever())
        self.assertEqual(summary["hybrid_query_rate"], 1.0)
        self.assertEqual(summary["bm25_fallback_rate"], 0.0)
        self.assertEqual(summary["dense_nonzero_hit_count"], 1)
        self.assertEqual(summary["document_vector_coverage"], 1.0)


class ScoringTest(unittest.TestCase):
    def setUp(self):
        self.question = load_questions(
            DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH, split="dev"
        )[0]

    @staticmethod
    def evidence(experiment_id: str, rank: int = 1, evidence_id: str = "E1"):
        return RetrievedEvidence(
            rank=rank,
            experiment_id=experiment_id,
            experiment_name=experiment_id,
            source_file=f"{experiment_id}.pdf",
            section="基础工具：不确定度计算",
            chunk_id=f"chunk-{experiment_id}",
            score=0.8,
            text="重复测量统计，仪器分度值，平方和开方。",
            evidence_id=evidence_id,
        )

    def test_experiment_id_matching_is_exact(self):
        prediction = Prediction(
            id=self.question.id,
            mode="blind",
            answer="重复测量统计，仪器分度值，平方和开方。[E1]",
            retrieved_evidence=[self.evidence("exp00")],
            citations=["E1"],
            grounded=True,
        )
        result = score_prediction(self.question, prediction)
        self.assertFalse(result["retrieval"]["recall_at_5"])

    def test_valid_retrieval_and_citation_are_recorded(self):
        prediction = Prediction(
            id=self.question.id,
            mode="blind",
            answer="A类来自重复测量统计，B类依据仪器分度值，二者平方和开方。[E1]",
            retrieved_evidence=[self.evidence("exp0")],
            citations=["E1"],
            grounded=True,
        )
        result = score_prediction(self.question, prediction)
        self.assertTrue(result["retrieval"]["recall_at_1"])
        self.assertEqual(result["citations"]["valid_rate"], 1.0)
        self.assertNotIn("invalid_citation", result["flags"])

    def test_context_expansion_is_a_legal_citation_source(self):
        prediction = Prediction(
            id=self.question.id,
            mode="blind",
            answer="A类来自重复测量统计，B类依据仪器分度值，二者平方和开方。",
            retrieved_evidence=[self.evidence("exp0", evidence_id="E1")],
            citations=["E1", "E2"],
            grounded=True,
            context_evidence=[
                ContextEvidence("E1", "exp0", "chunk-exp0"),
                ContextEvidence(
                    "E2", "exp0", "neighbor-exp0",
                    context_relation="adjacent_next",
                ),
            ],
            model_citations=None,
        )
        result = score_prediction(self.question, prediction)
        self.assertEqual(result["citations"]["valid_rate"], 1.0)
        self.assertFalse(result["citations"]["model_citations"]["available"])
        self.assertNotIn("invalid_citation", result["flags"])
        self.assertNotIn("missing_citation", result["flags"])

    def test_refusal_allows_an_inserted_adverb(self):
        boundary_question = next(
            item for item in load_questions(
                DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH, split="dev"
            ) if item.id == "B005"
        )
        prediction = Prediction(
            id="B005", mode="blind",
            answer="无法直接给出这些精确数值，需要现场测量。",
            retrieved_evidence=[], citations=[], grounded=False,
        )
        result = score_prediction(boundary_question, prediction)
        self.assertTrue(result["answer"]["refusal_detected"])
        self.assertTrue(result["answer"]["boundary_ok"])

    def test_boundary_distinguishes_qualified_post_refusal_help(self):
        boundary_question = next(
            item for item in load_questions(
                DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH, split="dev"
            ) if item.id == "D006"
        )

        cases = (
            (
                "较宽条纹一定对应细丝直径，公式为a sinθ=λ。",
                False, "unqualified_answer",
            ),
            (
                "现有资料不足，无法确定对应关系和公式。",
                True, "insufficient_only",
            ),
            (
                "现有资料不足，无法确定。仅供参考：一般性类比中可能用光栅模型。",
                True, "insufficient_with_qualified_supplement",
            ),
            (
                "现有资料不足，无法确定。但较宽条纹一定对应细丝直径。",
                False, "insufficient_then_unqualified_claim",
            ),
        )
        for answer, expected_ok, expected_class in cases:
            with self.subTest(expected_class=expected_class):
                prediction = Prediction(
                    id="D006", mode="blind", answer=answer,
                    retrieved_evidence=[], citations=[], grounded=False,
                )
                result = score_prediction(boundary_question, prediction)
                self.assertEqual(result["answer"]["boundary_ok"], expected_ok)
                self.assertEqual(result["answer"]["boundary_class"], expected_class)

    def test_math_and_synonym_normalization(self):
        self.assertEqual(normalized(r"$T_1^{2}$"), normalized("T1²"))
        self.assertEqual(normalized(r"4\pi"), normalized("4π"))
        self.assertEqual(normalized(r"1/\sqrt{2}"), normalized("0.707"))
        self.assertEqual(normalized("重新进行校准"), normalized("重新标定"))
        self.assertIn(normalized("u"), normalized("物距 $p$"))

    def test_report_keeps_split_breakdown(self):
        prediction = Prediction(
            id=self.question.id,
            mode="blind",
            answer="回答",
            retrieved_evidence=[],
            citations=[],
            grounded=False,
        )
        report = build_report([self.question], [prediction])
        self.assertEqual(report["summary"]["question_count"], 1)
        self.assertIn("dev", report["breakdowns"]["by_split"])


class CorpusAuditTest(unittest.TestCase):
    def test_missing_experiment_and_anchor_are_reported(self):
        question = load_questions(
            DEFAULT_QUESTIONS_PATH, DEFAULT_SCHEMA_PATH, split="dev"
        )[0]
        report = audit_corpus([question], [
            Chunk("x", "完全无关内容", "exp9", "其他", "x.pdf", "实验原理")
        ])
        self.assertIn("exp0", report["summary"]["missing_experiment_ids"])
        self.assertEqual(report["summary"]["anchor_presence_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
