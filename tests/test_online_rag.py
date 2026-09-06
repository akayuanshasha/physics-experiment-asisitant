from __future__ import annotations

import hashlib
import math
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from query_aliases import (
    build_query_variants,
    should_include_related_expansions,
)
from online_rag import (
    Chunk,
    CrossEncoderReranker,
    EmbeddingCache,
    HybridRetriever,
    RetrievalConfig,
    RetrievalHit,
    load_corpus,
)
from online_rag.corpus import (
    _REMOTE_EMBEDDING_OVERSIZE_CHUNK_IDS,
    _embedding_subchunk_id,
    _rechunk_embedding_oversize_chunks,
)
from online_rag.embeddings import (
    BM25OnlyEmbeddingBackend,
    EmbeddingConfig,
    EmbeddingServiceError,
    LocalEmbeddingConfig,
    LocalSentenceTransformerBackend,
    RemoteEmbeddingBackend,
)
from online_rag.factory import _embedding_backend_from_env
from online_rag.evaluation import EvaluationCase, evaluate_retriever, load_evaluation_cases
from online_rag.lexical import BM25Index, tokenize


class FakeEmbeddingBackend:
    model_name = "fake-physics-embedding"

    def __init__(self):
        self.document_calls = 0
        self.document_texts: list[str] = []
        self.document_batches: list[list[str]] = []

    @staticmethod
    def _vector(text: str) -> list[float]:
        terms = ("单摆", "重力", "电桥", "低电阻", "示波器", "触发")
        vector = [float(text.count(term)) for term in terms]
        if not any(vector):
            vector[-1] = 0.01
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls += 1
        self.document_texts.extend(texts)
        self.document_batches.append(list(texts))
        return [self._vector(text) for text in texts]

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]


def make_chunks() -> list[Chunk]:
    return [
        Chunk("a", "单摆周期可用于测量重力加速度。", "exp1", "单摆法测重力加速度", "a.pdf", "实验原理", 2, 2),
        Chunk("b", "双臂电桥适合测量低电阻。", "exp32", "双臂电桥", "b.pdf", "实验原理", 3, 3),
        Chunk("c", "示波器触发用于稳定显示波形。", "exp12", "示波器的使用", "c.pdf", "实验原理", 4, 4),
    ]


class LexicalTest(unittest.TestCase):
    def test_mixed_tokenizer_keeps_latin_and_chinese_bigrams(self):
        tokens = tokenize("F-H实验测量μ与Q值")
        self.assertIn("f-h", tokens)
        self.assertIn("实验", tokens)
        self.assertIn("q", tokens)

    def test_experiment_title_is_searchable(self):
        hits = BM25Index(make_chunks()).search("双臂电桥", top_k=1)
        self.assertEqual(hits[0][0], 1)

    def test_broad_uncertainty_questions_receive_deterministic_expansion(self):
        for question in ("如何计算不确定度", "不确定度怎么计算"):
            with self.subTest(question=question):
                include_related = should_include_related_expansions(question)
                variants = build_query_variants(
                    question, include_related=include_related, max_variants=8,
                )
                self.assertTrue(include_related)
                self.assertIn("A类标准不确定度", variants)
                self.assertIn("B类标准不确定度", variants)
                self.assertIn("合成标准不确定度", variants)

    def test_specific_uncertainty_question_is_not_broadly_expanded(self):
        self.assertFalse(
            should_include_related_expansions("A类标准不确定度如何计算")
        )


class CorpusTest(unittest.TestCase):
    def test_chunks_receive_parent_and_adjacent_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "exp1"
            directory.mkdir()
            (directory / "实验指导_提取文本.txt").write_text(
                "实验名称: 测试\n源文件: x.pdf\n====================\n"
                "实验原理\n" + "第一段内容。" * 30 + "\n" + "第二段内容。" * 30,
                encoding="utf-8",
            )
            chunks = load_corpus(
                tmp, target_chars=80, max_chars=120, overlap_chars=0,
            )

        self.assertGreaterEqual(len(chunks), 2)
        self.assertIsNotNone(chunks[0].parent_id)
        self.assertEqual(chunks[0].next_chunk_id, chunks[1].chunk_id)
        self.assertEqual(chunks[1].previous_chunk_id, chunks[0].chunk_id)

    def test_rag_markdown_preferred_and_metadata_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "exp1"
            directory.mkdir()
            (directory / "实验指导_提取文本.txt").write_text("旧内容", encoding="utf-8")
            (directory / "实验指导_RAG文本.md").write_text(
                "<!-- rag-extracted: v1 -->\n<!-- 实验名称: 测试实验 -->\n"
                "<!-- 源文件: source.pdf -->\n<!-- 页码:3 -->\n实验原理\n新内容。",
                encoding="utf-8",
            )
            chunks = load_corpus(tmp, target_chars=20, max_chars=50, overlap_chars=0)
        self.assertTrue(chunks)
        self.assertEqual(chunks[0].experiment_name, "测试实验")
        self.assertEqual(chunks[0].source, "source.pdf")
        self.assertEqual(chunks[0].section, "实验原理")
        self.assertEqual(chunks[0].page_start, 3)
        self.assertIn("新内容", chunks[0].text)
        self.assertNotIn("旧内容", chunks[0].text)

    def test_reviewed_reference_markdown_replaces_matching_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "experiment"
            root.mkdir()
            reference = Path(tmp) / "实验参考文档"
            reference.mkdir()
            (reference / "资料.pdf").write_bytes(b"not parsed because sidecar wins")
            (reference / "资料_RAG文本.md").write_text(
                "<!-- rag-extracted: v1 -->\n"
                "<!-- 实验名称: 审核资料 -->\n"
                "<!-- 源文件: 资料.pdf -->\n"
                "<!-- 页码:1 -->\n参考资料\n审核后的正文。",
                encoding="utf-8",
            )

            chunks = load_corpus(root, reference_root=reference, overlap_chars=0)

        self.assertTrue(chunks)
        self.assertEqual({chunk.source for chunk in chunks}, {"资料.pdf"})
        self.assertIn("审核后的正文", "".join(chunk.text for chunk in chunks))

    def test_chunk_ids_are_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "exp1"
            directory.mkdir()
            (directory / "实验指导_提取文本.txt").write_text(
                "实验名称: 测试\n源文件: x.pdf\n====================\n实验原理\n正文。",
                encoding="utf-8",
            )
            first = load_corpus(tmp, overlap_chars=0)
            second = load_corpus(tmp, overlap_chars=0)
        self.assertEqual([x.chunk_id for x in first], [x.chunk_id for x in second])

    def test_selective_embedding_rechunk_keeps_ordinary_chunks_stable(self):
        before = Chunk(
            "before", "before text", "exp1", "测试", "guide.pdf", "实验原理",
            parent_id="parent", next_chunk_id="long",
        )
        target = Chunk(
            "long", "abcdefghijklmnopqrstuvwxyz", "exp1", "测试", "guide.pdf",
            "实验原理", 1, 2, "parent", "before", "after",
            source_tier="secondary", source_kind="reference",
            authority="supplementary", is_example_data=True,
        )
        after = Chunk(
            "after", "after text", "exp1", "测试", "guide.pdf", "实验原理",
            parent_id="parent", previous_chunk_id="long",
        )
        chunks = [before, target, after]

        first = _rechunk_embedding_oversize_chunks(
            chunks, chunk_ids=frozenset({"long"}), maximum=10, overlap=3,
        )
        second = _rechunk_embedding_oversize_chunks(
            chunks, chunk_ids=frozenset({"long"}), maximum=10, overlap=3,
        )

        children = first[1:-1]
        self.assertEqual(first[0].chunk_id, "before")
        self.assertEqual(first[0].text, before.text)
        self.assertEqual(first[-1].chunk_id, "after")
        self.assertEqual(first[-1].text, after.text)
        self.assertNotIn("long", [chunk.chunk_id for chunk in first])
        self.assertEqual(
            [child.text for child in children],
            ["abcdefghij", "hijklmnopq", "opqrstuvwx", "vwxyz"],
        )
        for left, right in zip(children, children[1:]):
            self.assertEqual(left.text[-3:], right.text[:3])
        self.assertEqual(
            [child.chunk_id for child in children],
            [
                _embedding_subchunk_id("long", index, child.text)
                for index, child in enumerate(children)
            ],
        )
        self.assertEqual(
            [child.chunk_id for child in children],
            [child.chunk_id for child in second[1:-1]],
        )
        self.assertEqual(first[0].next_chunk_id, children[0].chunk_id)
        self.assertEqual(children[0].previous_chunk_id, "before")
        self.assertEqual(children[-1].next_chunk_id, "after")
        self.assertEqual(first[-1].previous_chunk_id, children[-1].chunk_id)
        for child in children:
            self.assertEqual(child.parent_id, target.parent_id)
            self.assertEqual(child.experiment_id, target.experiment_id)
            self.assertEqual(child.experiment_name, target.experiment_name)
            self.assertEqual(child.source, target.source)
            self.assertEqual(child.section, target.section)
            self.assertEqual(child.page_start, target.page_start)
            self.assertEqual(child.page_end, target.page_end)
            self.assertEqual(child.source_tier, target.source_tier)
            self.assertEqual(child.source_kind, target.source_kind)
            self.assertEqual(child.authority, target.authority)
            self.assertEqual(child.is_example_data, target.is_example_data)

    def test_load_corpus_rechunks_confirmed_remote_embedding_timeout_chunks(self):
        chunks = load_corpus()
        chunk_ids = {chunk.chunk_id for chunk in chunks}
        self.assertTrue(
            _REMOTE_EMBEDDING_OVERSIZE_CHUNK_IDS.isdisjoint(chunk_ids)
        )
        children = [
            chunk for chunk in chunks
            if chunk.source == "单摆法测重力加速度B（实验指导）.pdf"
            and chunk.section == "思考题"
            and (chunk.page_start, chunk.page_end) in {(5, 6), (6, 8), (8, 9)}
        ]
        self.assertEqual(len(children), 6)
        self.assertLessEqual(max(len(chunk.text) for chunk in children), 450)
        self.assertLessEqual(
            max(len(chunk.embedding_text()) for chunk in children), 460,
        )

    def test_legacy_experiment_id_is_replaced_by_canonical_source_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "exp35"
            directory.mkdir()
            (directory / "实验指导_提取文本.txt").write_text(
                "实验名称: exp35\n源文件: 迈氏干涉仪（实验指导）.pdf\n"
                "====================\n实验原理\n正文。",
                encoding="utf-8",
            )
            chunks = load_corpus(tmp, overlap_chars=0)
        self.assertEqual(chunks[0].experiment_name, "迈克耳孙干涉仪")

    def test_supplementary_markdown_is_loaded_without_replacing_primary_guide(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "exp1"
            supplement = directory / "RAG补充资料"
            supplement.mkdir(parents=True)
            (directory / "实验指导_提取文本.txt").write_text(
                "实验名称: 单摆法测重力加速度\n源文件: 单摆.pdf\n"
                "====================\n实验原理\n正式指导内容。",
                encoding="utf-8",
            )
            (supplement / "误差分析.md").write_text(
                "<!-- 源文件: 单摆补充资料.pdf -->\n<!-- 页码: 8 -->\n"
                "## 数据处理\n摆角过大会引入系统误差。",
                encoding="utf-8",
            )
            chunks = load_corpus(tmp, overlap_chars=0)
        self.assertEqual(len(chunks), 2)
        self.assertEqual({item.source for item in chunks}, {"单摆.pdf", "单摆补充资料.pdf"})
        added = next(item for item in chunks if item.source == "单摆补充资料.pdf")
        self.assertEqual(added.experiment_name, "单摆法测重力加速度")
        self.assertEqual(added.page_start, 8)
        self.assertIn("系统误差", added.text)

    def test_formula_explanation_and_table_rows_are_not_split_mid_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "exp5"
            directory.mkdir()
            (directory / "实验指导_RAG文本.md").write_text(
                "<!-- 实验名称: 杨氏模量 -->\n<!-- 源文件: test.pdf -->\n"
                "实验原理\n公式为：\n$$E=\\frac{FL}{A\\Delta L}$$\n"
                "式中 E 表示杨氏模量，F 表示拉力。\n"
                "| 参数 | 单位 |\n| --- | --- |\n| F | N |",
                encoding="utf-8",
            )
            chunks = load_corpus(
                tmp, target_chars=24, max_chars=32, overlap_chars=0,
            )
        formula = next(chunk.text for chunk in chunks if "\\frac" in chunk.text)
        table = next(chunk.text for chunk in chunks if "| 参数 |" in chunk.text)
        self.assertIn("公式为：", formula)
        self.assertIn("式中 E 表示", formula)
        self.assertIn("| --- | --- |", table)
        self.assertIn("| F | N |", table)


class HybridRetrieverTest(unittest.TestCase):
    def test_uncertainty_first_questions_cross_default_bm25_gate(self):
        retriever = HybridRetriever(
            load_corpus(), BM25OnlyEmbeddingBackend(),
            config=RetrievalConfig(dense_weight=0.0),
        )

        for question in ("如何计算不确定度", "不确定度怎么计算"):
            with self.subTest(question=question):
                result = retriever.retrieve(question, top_k=12)
                eligible = [hit for hit in result.hits if hit.lexical_score >= 50.0]
                self.assertTrue(eligible)
                self.assertTrue(
                    any(hit.chunk.experiment_id == "exp0" for hit in eligible)
                )

    def test_cross_encoder_reranks_candidates(self):
        class ReverseModel:
            @staticmethod
            def predict(pairs):
                return list(range(len(pairs)))

        chunks = make_chunks()[:2]
        baseline = HybridRetriever(
            chunks, FakeEmbeddingBackend(),
            config=RetrievalConfig(dense_weight=0.0, rerank_candidate_k=2),
        ).retrieve("实验", top_k=2)
        reranker = CrossEncoderReranker("fake", model=ReverseModel())
        reranked = HybridRetriever(
            chunks, FakeEmbeddingBackend(),
            config=RetrievalConfig(dense_weight=0.0, rerank_candidate_k=2),
            reranker=reranker,
        ).retrieve("实验", top_k=2)

        self.assertEqual(
            reranked.hits[0].chunk.chunk_id,
            baseline.hits[-1].chunk.chunk_id,
        )
        self.assertIsNotNone(reranked.hits[0].rerank_score)

    def test_context_expansion_adds_parent_neighbors_without_changing_hits(self):
        chunks = [
            Chunk("a", "前文", "exp1", "测试", "x.pdf", "原理", 1, 1,
                  "parent", None, "b"),
            Chunk("b", "命中", "exp1", "测试", "x.pdf", "原理", 1, 2,
                  "parent", "a", "c"),
            Chunk("c", "后文", "exp1", "测试", "x.pdf", "原理", 2, 2,
                  "parent", "b", None),
        ]
        retriever = HybridRetriever(
            chunks, FakeEmbeddingBackend(),
            config=RetrievalConfig(dense_weight=0.0),
        )
        original = [RetrievalHit(chunks[1], score=1.0)]

        expanded = retriever.expand_context(original, neighbors=1)

        self.assertEqual([hit.chunk.chunk_id for hit in original], ["b"])
        self.assertEqual([hit.chunk.chunk_id for hit in expanded], ["b", "a", "c"])
        self.assertEqual(expanded[1].context_relation, "parent_previous")
        self.assertEqual(expanded[2].context_relation, "parent_next")

    def test_intentionally_disabled_dense_search_reports_plain_bm25(self):
        retriever = HybridRetriever(
            make_chunks(),
            FakeEmbeddingBackend(),
            config=RetrievalConfig(dense_weight=0.0, lexical_weight=1.0),
        )

        result = retriever.retrieve("干涉条纹")

        self.assertEqual(result.retrieval_mode, "bm25")

    def _config(self, cache_path: Path) -> RetrievalConfig:
        return RetrievalConfig(cache_path=cache_path, dense_score_threshold=0.1)

    def test_alias_query_retrieves_canonical_experiment(self):
        with tempfile.TemporaryDirectory() as tmp:
            backend = FakeEmbeddingBackend()
            retriever = HybridRetriever(make_chunks(), backend, self._config(Path(tmp) / "cache.json"))
            result = retriever.retrieve("开尔文电桥为什么能测低电阻", top_k=2)
        self.assertEqual(result.hits[0].chunk.experiment_id, "exp32")
        self.assertIn("双臂电桥", result.query_variants)
        self.assertGreater(result.hits[0].lexical_score, 0)
        self.assertGreater(result.hits[0].dense_score, 0)

    def test_embedding_cache_avoids_reembedding_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "cache.json"
            first_backend = FakeEmbeddingBackend()
            HybridRetriever(make_chunks(), first_backend, self._config(cache))
            second_backend = FakeEmbeddingBackend()
            HybridRetriever(make_chunks(), second_backend, self._config(cache))
        self.assertEqual(first_backend.document_calls, 1)
        self.assertEqual(second_backend.document_calls, 0)

    def test_rechunked_index_reuses_cached_ordinary_vectors_and_embeds_missing_children(self):
        original = [
            Chunk(
                "cached", "单摆周期可用于测量重力加速度。", "exp1",
                "单摆法测重力加速度", "guide.pdf", "实验原理",
                parent_id="parent", next_chunk_id="long",
            ),
            Chunk(
                "long", "abcdefghijklmnopqrstuvwxyz", "exp1",
                "单摆法测重力加速度", "guide.pdf", "实验原理",
                parent_id="parent", previous_chunk_id="cached",
            ),
        ]
        chunks = _rechunk_embedding_oversize_chunks(
            original, chunk_ids=frozenset({"long"}), maximum=10, overlap=3,
        )

        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "cache.json"
            cached_chunk = chunks[0]
            cache = EmbeddingCache(cache_path, FakeEmbeddingBackend.model_name)
            text_hash = hashlib.sha256(
                cached_chunk.embedding_text().encode("utf-8")
            ).hexdigest()
            cache.put(
                cached_chunk.chunk_id, text_hash,
                FakeEmbeddingBackend._vector(cached_chunk.embedding_text()),
            )
            cache.save()

            backend = FakeEmbeddingBackend()
            retriever = HybridRetriever(
                chunks,
                backend,
                RetrievalConfig(
                    cache_path=cache_path,
                    dense_score_threshold=0.1,
                    document_embedding_batch_size=2,
                ),
            )
            status = retriever.status()

        self.assertEqual(len(retriever.document_vectors), len(chunks))
        self.assertEqual(backend.document_calls, 2)
        self.assertNotIn(cached_chunk.embedding_text(), backend.document_texts)
        self.assertEqual(
            backend.document_texts,
            [chunk.embedding_text() for chunk in chunks[1:]],
        )
        self.assertTrue(status["dense_available"])
        self.assertEqual(status["cache"]["current_entries"], len(chunks))
        self.assertEqual(status["cache"]["missing_current_entries"], 0)

    def test_empty_query_returns_no_hits(self):
        with tempfile.TemporaryDirectory() as tmp:
            retriever = HybridRetriever(
                make_chunks(), FakeEmbeddingBackend(), self._config(Path(tmp) / "cache.json")
            )
            result = retriever.retrieve("   ")
        self.assertEqual(result.hits, [])

    def test_result_is_json_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            retriever = HybridRetriever(
                make_chunks(), FakeEmbeddingBackend(), self._config(Path(tmp) / "cache.json")
            )
            data = retriever.retrieve("示波器如何同步", top_k=1).to_dict()
        self.assertEqual(data["hits"][0]["experiment_id"], "exp12")
        self.assertIn("timings_ms", data)

    def test_explicit_short_experiment_title_beats_longer_related_title(self):
        chunks = [
            Chunk("short", "拉伸法测量内容。", "exp5", "杨氏模量B", "a.pdf", "实验原理"),
            Chunk(
                "long", "拉伸法测量内容。", "exp40", "测量金属丝的杨氏模量及泊松比",
                "b.pdf", "实验原理",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            retriever = HybridRetriever(
                chunks, FakeEmbeddingBackend(), self._config(Path(tmp) / "cache.json")
            )
            result = retriever.retrieve("拉伸法测杨氏模量", top_k=2)
        self.assertEqual(result.hits[0].chunk.experiment_id, "exp5")

    def test_page_context_is_a_soft_priority_and_keeps_cross_experiment_hits(self):
        chunks = [
            Chunk("a", "公共误差分析方法。", "exp1", "单摆", "a.pdf", "数据处理"),
            Chunk("b", "公共误差分析方法。", "exp32", "双臂电桥", "b.pdf", "数据处理"),
        ]
        retriever = HybridRetriever(
            chunks, FakeEmbeddingBackend(),
            RetrievalConfig(dense_weight=0.0, max_hits_per_source_first_pass=2),
        )
        result = retriever.retrieve("误差分析方法", top_k=2, experiment_ids=["exp32"])
        self.assertEqual(result.hits[0].chunk.experiment_id, "exp32")
        self.assertEqual({hit.chunk.experiment_id for hit in result.hits}, {"exp1", "exp32"})

    def test_strict_page_context_remains_available(self):
        retriever = HybridRetriever(
            make_chunks(), FakeEmbeddingBackend(),
            RetrievalConfig(dense_weight=0.0, strict_page_context=True),
        )
        result = retriever.retrieve("实验原理", top_k=3, experiment_ids=["exp32"])
        self.assertTrue(result.hits)
        self.assertEqual({hit.chunk.experiment_id for hit in result.hits}, {"exp32"})

    def test_source_diversity_precedes_extra_hits_from_one_source(self):
        chunks = [
            Chunk("a1", "误差分析方法甲。", "exp1", "实验甲", "a.pdf", "数据处理"),
            Chunk("a2", "误差分析方法乙。", "exp1", "实验甲", "a.pdf", "数据处理"),
            Chunk("a3", "误差分析方法丙。", "exp1", "实验甲", "a.pdf", "数据处理"),
            Chunk("b1", "误差分析方法丁。", "exp2", "实验乙", "b.pdf", "数据处理"),
        ]
        retriever = HybridRetriever(
            chunks, FakeEmbeddingBackend(),
            RetrievalConfig(dense_weight=0.0, max_hits_per_source_first_pass=2),
        )
        result = retriever.retrieve("误差分析方法", top_k=3)
        self.assertIn("b.pdf", [hit.chunk.source for hit in result.hits])
        self.assertLessEqual(
            sum(hit.chunk.source == "a.pdf" for hit in result.hits), 2,
        )

    def test_primary_guide_excludes_matching_secondary_when_sufficient(self):
        chunks = [
            Chunk(
                "reference", "A类不确定度 B类不确定度 平方和开方。",
                "reference:review", "综合复习资料", "review.md", "参考资料",
                source_tier="secondary", source_kind="reference",
                authority="supplementary",
            ),
            Chunk(
                "formal", "A类不确定度 B类不确定度 平方和开方。",
                "exp0", "不确定度计算", "guide.md", "实验原理",
            ),
        ]
        retriever = HybridRetriever(
            chunks, FakeEmbeddingBackend(),
            RetrievalConfig(
                dense_weight=0.0,
                max_hits_per_source_first_pass=2,
                primary_minimum_bm25_score=0.0,
            ),
        )

        result = retriever.retrieve("A类不确定度和B类不确定度如何平方和开方", top_k=2)

        self.assertEqual([hit.chunk.experiment_id for hit in result.hits], ["exp0"])
        self.assertEqual(result.authority_mode, "primary_only")

    def test_secondary_is_enabled_only_when_primary_is_below_threshold(self):
        chunks = [
            Chunk(
                "primary", "报告格式说明。", "exp1", "正式讲义",
                "guide.md", "实验要求",
            ),
            Chunk(
                "secondary", "报告格式与排版建议。", "reference:guide",
                "实验指北", "reference.md", "参考资料",
                source_tier="secondary", source_kind="reference",
                authority="supplementary",
            ),
        ]
        retriever = HybridRetriever(
            chunks, BM25OnlyEmbeddingBackend(),
            RetrievalConfig(
                dense_weight=0.0,
                primary_minimum_bm25_score=1_000_000.0,
            ),
        )

        result = retriever.retrieve("报告格式排版建议", top_k=2)

        self.assertEqual(result.authority_mode, "primary_with_secondary_fallback")
        self.assertIn("secondary", [hit.chunk.source_tier for hit in result.hits])

    def test_example_data_requires_explicit_example_intent(self):
        chunks = [
            Chunk(
                "primary", "切变模量计算格式。", "exp6", "切变模量",
                "guide.md", "数据处理",
            ),
            Chunk(
                "example", "切变模量示例演示计算格式。", "exp6", "切变模量",
                "example.csv", "示例数据", source_tier="example",
                source_kind="example_data", authority="example_only",
                is_example_data=True,
            ),
        ]
        retriever = HybridRetriever(
            chunks, BM25OnlyEmbeddingBackend(),
            RetrievalConfig(
                dense_weight=0.0,
                primary_minimum_bm25_score=0.0,
                max_hits_per_source_first_pass=2,
            ),
        )

        ordinary = retriever.retrieve("切变模量计算格式", top_k=2)
        explicit = retriever.retrieve("请用示例演示切变模量计算格式", top_k=2)

        self.assertEqual([hit.chunk.source_tier for hit in ordinary.hits], ["primary"])
        self.assertFalse(ordinary.example_data_enabled)
        self.assertIn("example", [hit.chunk.source_tier for hit in explicit.hits])
        self.assertTrue(explicit.example_data_enabled)

    def test_document_embedding_failure_falls_back_to_bm25(self):
        class FailingDocumentBackend(FakeEmbeddingBackend):
            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                raise EmbeddingServiceError("service unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            retriever = HybridRetriever(
                make_chunks(), FailingDocumentBackend(),
                self._config(Path(tmp) / "cache.json"),
            )
            result = retriever.retrieve("双臂电桥测低电阻", top_k=1)

        self.assertEqual(result.retrieval_mode, "bm25_fallback")
        self.assertEqual(result.hits[0].chunk.experiment_id, "exp32")
        self.assertTrue(any("回退 BM25" in item for item in result.warnings))

    def test_query_embedding_failure_disables_dense_for_later_queries(self):
        class FailingQueryBackend(FakeEmbeddingBackend):
            def embed_queries(self, texts: list[str]) -> list[list[float]]:
                raise EmbeddingServiceError("query endpoint unavailable")

        backend = FailingQueryBackend()
        with tempfile.TemporaryDirectory() as tmp:
            retriever = HybridRetriever(
                make_chunks(), backend, self._config(Path(tmp) / "cache.json"),
            )
            first = retriever.retrieve("示波器触发", top_k=1)
            second = retriever.retrieve("单摆重力", top_k=1)

        self.assertEqual(first.retrieval_mode, "bm25_fallback")
        self.assertEqual(second.retrieval_mode, "bm25_fallback")
        self.assertFalse(retriever.dense_available)

    def test_fallback_can_be_disabled_for_strict_evaluation(self):
        class FailingDocumentBackend(FakeEmbeddingBackend):
            def embed_documents(self, texts: list[str]) -> list[list[float]]:
                raise EmbeddingServiceError("service unavailable")

        with tempfile.TemporaryDirectory() as tmp:
            config = RetrievalConfig(
                cache_path=Path(tmp) / "cache.json",
                dense_score_threshold=0.1,
                allow_bm25_fallback=False,
            )
            with self.assertRaises(EmbeddingServiceError):
                HybridRetriever(make_chunks(), FailingDocumentBackend(), config)


class RemoteEmbeddingBackendTest(unittest.TestCase):
    class _Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.close()

    def test_config_accepts_llm_credentials_but_keeps_embedding_model_separate(self):
        env = {
            "LLM_BASE_URL": "https://example.test/v1",
            "LLM_API_KEY": "secret",
            "EMBEDDING_MODEL": "embedding-model",
        }
        with patch.dict("os.environ", env, clear=True):
            config = EmbeddingConfig.from_env()
        self.assertEqual(config.base_url, env["LLM_BASE_URL"])
        self.assertEqual(config.api_key, env["LLM_API_KEY"])
        self.assertEqual(config.model, "embedding-model")
        self.assertEqual(config.proxy_mode, "direct")

    def test_embedding_proxy_inherits_chat_proxy_by_default(self):
        env = {
            "LLM_BASE_URL": "https://example.test/v1",
            "LLM_API_KEY": "secret",
            "EMBEDDING_MODEL": "embedding-model",
            "CHAT_PROXY_MODE": "custom",
            "CHAT_PROXY_URL": "http://proxy.test:8080",
        }
        with patch.dict("os.environ", env, clear=True):
            config = EmbeddingConfig.from_env()
        self.assertEqual(config.proxy_mode, "custom")
        self.assertEqual(config.proxy_url, "http://proxy.test:8080")

    def test_embedding_proxy_can_override_chat_proxy(self):
        env = {
            "LLM_BASE_URL": "https://example.test/v1",
            "LLM_API_KEY": "secret",
            "EMBEDDING_MODEL": "embedding-model",
            "CHAT_PROXY_MODE": "system",
            "EMBEDDING_PROXY_MODE": "direct",
        }
        with patch.dict("os.environ", env, clear=True):
            config = EmbeddingConfig.from_env()
        self.assertEqual(config.proxy_mode, "direct")

    def test_response_is_reordered_by_index_and_normalized(self):
        body = json.dumps({"data": [
            {"index": 1, "embedding": [0, 3]},
            {"index": 0, "embedding": [4, 0]},
        ]}).encode("utf-8")
        config = EmbeddingConfig(
            "https://example.test/v1", "secret", "embedding-model", max_attempts=1,
        )
        opener = Mock()
        opener.open.return_value = self._Response(body)
        vectors = RemoteEmbeddingBackend(config, opener=opener).embed_queries(["甲", "乙"])
        self.assertEqual(vectors, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(
            opener.open.call_args.args[0].full_url,
            "https://example.test/v1/embeddings",
        )

    def test_response_with_all_duplicate_indices_uses_provider_order(self):
        body = json.dumps({"data": [
            {"index": 0, "embedding": [4, 0]},
            {"index": 0, "embedding": [0, 3]},
        ]}).encode("utf-8")
        config = EmbeddingConfig(
            "https://example.test/v1", "secret", "embedding-model", max_attempts=1,
        )
        opener = Mock()
        opener.open.return_value = self._Response(body)
        backend = RemoteEmbeddingBackend(config, opener=opener)
        vectors = backend.embed_queries(["甲", "乙"])
        self.assertEqual(vectors, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(backend.health()["positional_index_fallbacks"], 1)

    def test_response_with_partial_duplicate_indices_is_rejected(self):
        body = json.dumps({"data": [
            {"index": 0, "embedding": [1, 0]},
            {"index": 0, "embedding": [0, 1]},
            {"index": 2, "embedding": [1, 1]},
        ]}).encode("utf-8")
        config = EmbeddingConfig(
            "https://example.test/v1", "secret", "embedding-model", max_attempts=1,
        )
        opener = Mock()
        opener.open.return_value = self._Response(body)
        with self.assertRaisesRegex(EmbeddingServiceError, "index 缺失或重复"):
            RemoteEmbeddingBackend(config, opener=opener).embed_queries(["甲", "乙", "丙"])

    def test_malformed_response_raises_domain_error(self):
        body = json.dumps({"data": []}).encode("utf-8")
        config = EmbeddingConfig(
            "https://example.test/v1/embeddings", "secret", "embedding-model",
            max_attempts=1,
        )
        opener = Mock()
        opener.open.return_value = self._Response(body)
        with self.assertRaises(EmbeddingServiceError):
            RemoteEmbeddingBackend(config, opener=opener).embed_queries(["测试"])

    def test_direct_mode_builds_embedding_opener_without_proxies(self):
        config = EmbeddingConfig(
            "https://example.test/v1", "secret", "embedding-model",
        )
        with patch("online_rag.embeddings.build_opener") as build:
            build.return_value = Mock()
            RemoteEmbeddingBackend(config)
        self.assertEqual(build.call_args.args[0].proxies, {})

    def test_custom_mode_uses_configured_embedding_proxy(self):
        config = EmbeddingConfig(
            "https://example.test/v1", "secret", "embedding-model",
            proxy_mode="custom", proxy_url="http://proxy.test:8080",
        )
        with patch("online_rag.embeddings.build_opener") as build:
            build.return_value = Mock()
            RemoteEmbeddingBackend(config)
        self.assertEqual(build.call_args.args[0].proxies, {
            "http": "http://proxy.test:8080",
            "https": "http://proxy.test:8080",
        })


class LocalEmbeddingBackendTest(unittest.TestCase):
    class _Model:
        def __init__(self):
            self.kwargs = None

        def encode(self, texts, **kwargs):
            self.kwargs = kwargs
            return [[3.0, 4.0] for _ in texts]

    def test_local_backend_normalizes_vectors_without_loading_dependency(self):
        model = self._Model()
        backend = LocalSentenceTransformerBackend(
            LocalEmbeddingConfig("local-model", batch_size=7), model=model,
        )
        vectors = backend.embed_queries(["甲", "乙"])
        self.assertEqual(vectors, [[0.6, 0.8], [0.6, 0.8]])
        self.assertEqual(model.kwargs["batch_size"], 7)
        self.assertTrue(model.kwargs["normalize_embeddings"])

    def test_factory_can_explicitly_disable_dense_retrieval(self):
        with patch.dict("os.environ", {"RAG_EMBEDDING_BACKEND": "bm25"}, clear=True):
            backend, config = _embedding_backend_from_env(None, RetrievalConfig())
        self.assertIsInstance(backend, BM25OnlyEmbeddingBackend)
        self.assertEqual(config.dense_weight, 0.0)

    def test_factory_selects_local_backend_without_loading_model(self):
        env = {
            "RAG_EMBEDDING_BACKEND": "local",
            "LOCAL_EMBEDDING_MODEL": "D:/models/text2vec",
        }
        with patch.dict("os.environ", env, clear=True):
            backend, config = _embedding_backend_from_env(None, RetrievalConfig())
        self.assertIsInstance(backend, LocalSentenceTransformerBackend)
        self.assertEqual(backend.config.model, env["LOCAL_EMBEDDING_MODEL"])
        self.assertTrue(backend.config.local_files_only)
        self.assertGreater(config.dense_weight, 0.0)


class EvaluationTest(unittest.TestCase):
    def test_fixture_contains_thirty_cases(self):
        path = Path(__file__).parent / "fixtures" / "online_rag_retrieval_cases.json"
        cases = load_evaluation_cases(path)
        self.assertEqual(len(cases), 30)

    def test_metrics_are_computed_without_llm_judge(self):
        with tempfile.TemporaryDirectory() as tmp:
            retriever = HybridRetriever(
                make_chunks(), FakeEmbeddingBackend(),
                RetrievalConfig(cache_path=Path(tmp) / "cache.json", dense_score_threshold=0.1),
            )
            report = evaluate_retriever(retriever, [
                EvaluationCase("单摆怎么测重力", ("exp1",)),
                EvaluationCase("开尔文电桥测低电阻", ("exp32",)),
            ], top_k=2)
        self.assertEqual(report["recall_at_2"], 1.0)
        self.assertGreater(report["mrr"], 0.0)


if __name__ == "__main__":
    unittest.main()
