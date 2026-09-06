from __future__ import annotations

import unittest

from online_rag import (
    AssistantConfig,
    ChatServiceError,
    Chunk,
    ContextConfig,
    HistoryQuestionRewriter,
    HybridRetriever,
    PhysicsExperimentAssistant,
    RetrievalHit,
    RetrievalResult,
    RewriteResult,
    build_context,
)


def make_hit(
    chunk_id: str,
    text: str,
    *,
    experiment_id: str = "exp12",
    experiment_name: str = "示波器的使用",
    section: str = "实验原理",
    score: float = 0.8,
) -> RetrievalHit:
    return RetrievalHit(
        Chunk(
            chunk_id=chunk_id,
            text=text,
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            source=f"{experiment_name}（实验指导）.pdf",
            section=section,
            page_start=3,
            page_end=3,
        ),
        score=score,
        lexical_score=4.0,
        dense_score=0.75,
    )


class FakeRetriever:
    def __init__(self, hits: list[RetrievalHit]):
        self.hits = hits
        self.calls = 0
        self.last_top_k: int | None = None
        self.last_question: str | None = None

    def retrieve(self, question: str, top_k: int = 6) -> RetrievalResult:
        self.calls += 1
        self.last_top_k = top_k
        self.last_question = question
        return RetrievalResult(
            query=question,
            normalized_query=question,
            query_variants=[question],
            hits=self.hits[:top_k],
        )


class FakeChatBackend:
    model_name = "fake-chat"

    def __init__(self, answer: str):
        self.answer = answer
        self.calls = 0
        self.messages: list[dict[str, str]] = []
        self.options: dict = {}

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.1,
        max_tokens: int = 1200,
    ) -> str:
        self.calls += 1
        self.messages = messages
        self.options = {"temperature": temperature, "max_tokens": max_tokens}
        return self.answer


class FailingChatBackend(FakeChatBackend):
    def complete(self, messages, *, temperature=0.1, max_tokens=1200):
        self.calls += 1
        raise RuntimeError("chat unavailable")


class StreamingChatBackend(FakeChatBackend):
    def stream_complete(self, messages, *, temperature=0.1, max_tokens=1200):
        self.calls += 1
        self.messages = messages
        yield "流式"
        yield "回答。[E1]"


class StreamFailsBeforeTokenBackend(FakeChatBackend):
    def __init__(self, answer: str):
        super().__init__(answer)
        self.stream_calls = 0

    def stream_complete(self, messages, *, temperature=0.1, max_tokens=1200):
        self.stream_calls += 1
        if False:
            yield ""
        raise ChatServiceError("stream unavailable", stage="stream_connect")


class PartialStreamFailsBackend(FakeChatBackend):
    def __init__(self):
        super().__init__("不应调用非流式")
        self.stream_calls = 0

    def stream_complete(self, messages, *, temperature=0.1, max_tokens=1200):
        self.stream_calls += 1
        yield "已经显示给用户的部分回答。" * 12
        raise ChatServiceError(
            "stream interrupted", stage="stream_read", partial=True,
        )


class AllGenerationFailsBackend(StreamFailsBeforeTokenBackend):
    def complete(self, messages, *, temperature=0.1, max_tokens=1200):
        self.calls += 1
        raise ChatServiceError("fallback unavailable", stage="transport")


class FixedQuestionRewriter:
    def rewrite(self, question, history=None):
        return RewriteResult("杨氏模量实验的不确定度如何计算？", rewritten=True)


class ContextBuilderTest(unittest.TestCase):
    def test_duplicate_evidence_is_removed_and_ids_are_stable(self):
        repeated = "触发电路使每次扫描从输入信号的同一相位开始，从而稳定显示波形。" * 3
        hits = [
            make_hit("a", repeated),
            make_hit("b", repeated + "补充说明。"),
            make_hit(
                "c", "双臂电桥能够减小引线电阻和接触电阻的影响。",
                experiment_id="exp32", experiment_name="双臂电桥",
            ),
        ]
        package = build_context(hits)
        self.assertEqual([item.evidence_id for item in package.evidence], ["E1", "E2"])
        self.assertEqual(package.evidence[1].chunk.experiment_id, "exp32")
        self.assertTrue(any("重复证据" in warning for warning in package.warnings))

    def test_context_obeys_hard_character_budget(self):
        package = build_context(
            [make_hit("a", "示波器实验内容。" * 100)],
            ContextConfig(max_evidence=2, max_context_chars=130),
        )
        self.assertLessEqual(len(package.text), 130)
        self.assertEqual(len(package.evidence), 1)
        self.assertTrue(package.evidence[0].truncated)

    def test_per_experiment_limit_preserves_diversity(self):
        hits = [
            make_hit("a", "第一段不同内容。"),
            make_hit("b", "第二段完全不同的步骤说明。", section="实验步骤"),
            make_hit(
                "c", "低电阻测量内容。", experiment_id="exp32",
                experiment_name="双臂电桥",
            ),
        ]
        package = build_context(
            hits, ContextConfig(max_evidence=3, max_chunks_per_experiment=1),
        )
        self.assertEqual(
            [item.chunk.experiment_id for item in package.evidence],
            ["exp12", "exp32"],
        )

class HistoryQuestionRewriterTest(unittest.TestCase):
    def setUp(self):
        self.history = [
            {"role": "user", "content": "杨氏模量实验怎样计算结果？"},
            {"role": "assistant", "content": "需要测量载荷和伸长量。"},
        ]

    def test_standalone_question_does_not_call_model(self):
        chat = FakeChatBackend("不应被调用")
        result = HistoryQuestionRewriter(chat).rewrite(
            "单摆法如何计算重力加速度？", self.history,
        )
        self.assertFalse(result.rewritten)
        self.assertEqual(chat.calls, 0)

    def test_follow_up_question_is_rewritten(self):
        chat = FakeChatBackend("杨氏模量实验的不确定度如何计算？")
        result = HistoryQuestionRewriter(chat).rewrite("那它的不确定度呢？", self.history)
        self.assertTrue(result.rewritten)
        self.assertIn("杨氏模量", result.question)
        self.assertEqual(chat.calls, 1)

    def test_short_standalone_question_is_not_rewritten_with_history(self):
        chat = FakeChatBackend("不应被调用")
        result = HistoryQuestionRewriter(chat).rewrite(
            "不确定度怎么计算", self.history,
        )
        self.assertFalse(result.rewritten)
        self.assertEqual(result.question, "不确定度怎么计算")
        self.assertEqual(chat.calls, 0)

    def test_vague_short_follow_up_is_rewritten(self):
        chat = FakeChatBackend("杨氏模量实验的结果怎么算？")
        result = HistoryQuestionRewriter(chat).rewrite("怎么算？", self.history)
        self.assertTrue(result.rewritten)
        self.assertEqual(chat.calls, 1)

    def test_rewrite_failure_uses_deterministic_context(self):
        chat = FailingChatBackend("")
        result = HistoryQuestionRewriter(chat).rewrite("那它呢？", self.history)
        self.assertTrue(result.rewritten)
        self.assertIn("前一个问题", result.question)
        self.assertIn("杨氏模量", result.question)
        self.assertIn("确定性回退", result.warning or "")


class AssistantTest(unittest.TestCase):
    def test_standalone_short_question_is_history_independent(self):
        retriever = FakeRetriever([
            make_hit("uncertainty", "A类与B类标准不确定度合成为合成标准不确定度。")
        ])
        chat = FakeChatBackend("按A类、B类和合成标准不确定度依次计算。[E1]")
        assistant = PhysicsExperimentAssistant(
            retriever, chat, question_rewriter=HistoryQuestionRewriter(chat),
        )
        history = [
            {"role": "user", "content": "如何计算不确定度"},
            {"role": "assistant", "content": "上一轮回答。"},
        ]

        without_history = assistant.ask("不确定度怎么计算")
        with_history = assistant.ask(
            "不确定度怎么计算", conversation_history=history,
        )

        self.assertEqual(without_history.retrieval_question, "不确定度怎么计算")
        self.assertEqual(with_history.retrieval_question, "不确定度怎么计算")
        self.assertFalse(without_history.history_rewrite_used)
        self.assertFalse(with_history.history_rewrite_used)

    def test_stream_emits_meta_tokens_and_validated_done_result(self):
        assistant = PhysicsExperimentAssistant(
            FakeRetriever([make_hit("stream", "流式证据。")]),
            StreamingChatBackend(""),
        )

        events = list(assistant.ask_stream("问题"))

        self.assertEqual(events[0]["type"], "meta")
        self.assertEqual(events[-1]["type"], "done")
        streamed = "".join(
            event["text"] for event in events if event["type"] == "token"
        )
        self.assertEqual(streamed, "流式回答。")
        self.assertNotIn("[E1]", events[-1]["result"].answer)
        self.assertTrue(events[-1]["result"].grounded)

    def test_stream_failure_before_token_falls_back_to_nonstream(self):
        chat = StreamFailsBeforeTokenBackend("非流式回答。[E1]")
        assistant = PhysicsExperimentAssistant(
            FakeRetriever([make_hit("fallback", "降级证据。")]), chat,
        )

        events = list(assistant.ask_stream("问题"))
        streamed = "".join(
            event["text"] for event in events if event["type"] == "token"
        )
        result = events[-1]["result"]

        self.assertEqual(streamed, "非流式回答。")
        self.assertEqual(chat.stream_calls, 1)
        self.assertEqual(chat.calls, 1)
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.generation_mode, "nonstream_fallback")

    def test_no_evidence_notice_waits_for_successful_fallback(self):
        chat = StreamFailsBeforeTokenBackend("通用知识回答。")
        events = list(
            PhysicsExperimentAssistant(FakeRetriever([]), chat).ask_stream("问题")
        )
        tokens = [event["text"] for event in events if event["type"] == "token"]
        self.assertEqual(len(tokens), 1)
        self.assertTrue(tokens[0].startswith("当前实验资料"))
        self.assertEqual(tokens[0].count("上传相关实验资料"), 1)

    def test_no_evidence_notice_is_not_emitted_when_all_generation_fails(self):
        events = []
        assistant = PhysicsExperimentAssistant(
            FakeRetriever([]), AllGenerationFailsBackend(""),
        )
        with self.assertRaises(ChatServiceError):
            for event in assistant.ask_stream("问题"):
                events.append(event)
        self.assertFalse(any(event["type"] == "token" for event in events))

    def test_partial_stream_failure_does_not_restart_generation(self):
        chat = PartialStreamFailsBackend()
        events = []
        assistant = PhysicsExperimentAssistant(
            FakeRetriever([make_hit("partial", "部分回答证据。")]), chat,
        )
        with self.assertRaises(ChatServiceError):
            for event in assistant.ask_stream("问题"):
                events.append(event)
        self.assertTrue(any(event["type"] == "token" for event in events))
        self.assertEqual(chat.calls, 0)

    def test_default_bm25_threshold_rejects_weak_lexical_hit(self):
        hit = make_hit("weak", "主题词偶然重合。", score=0.04)
        hit.lexical_score = 20.0
        retrieval = RetrievalResult(
            "问题", "问题", ["问题"], [hit], retrieval_mode="bm25",
        )

        class Bm25Retriever:
            @staticmethod
            def retrieve(question, top_k=6):
                return retrieval

        chat = FakeChatBackend("可以先检查仪器零点和操作步骤。")
        assistant = PhysicsExperimentAssistant(Bm25Retriever(), chat)
        result = assistant.ask("问题")

        self.assertFalse(result.grounded)
        self.assertEqual(chat.calls, 1)
        self.assertIn("上传相关实验资料", result.answer)
        self.assertTrue(any("最低相关性" in item for item in result.warnings))
        self.assertEqual(result.retrieval_diagnostics["retrieved_count"], 1)
        self.assertEqual(result.retrieval_diagnostics["eligible_count"], 0)
        self.assertEqual(result.retrieval_diagnostics["filtered_count"], 1)
        self.assertEqual(result.retrieval_diagnostics["maximum_lexical_score"], 20.0)

    def setUp(self):
        self.hit = make_hit("a", "触发同步能够使示波器显示稳定的周期波形。")

    def test_complete_grounded_answer_and_json_result(self):
        retriever = FakeRetriever([self.hit])
        chat = FakeChatBackend("调节触发电平可以帮助波形稳定显示。[E1]\n\n依据：[E1]")
        assistant = PhysicsExperimentAssistant(retriever, chat)
        result = assistant.ask("示波器触发同步怎么调？")

        self.assertTrue(result.grounded)
        self.assertEqual([item.evidence_id for item in result.citations], ["E1"])
        self.assertNotIn("[E1]", result.answer)
        self.assertNotIn("依据：", result.answer)
        self.assertEqual(retriever.last_top_k, 12)
        self.assertIn("<evidence>", chat.messages[1]["content"])
        self.assertIn("触发同步能够", chat.messages[1]["content"])
        self.assertEqual(result.to_dict()["citations"][0]["experiment_id"], "exp12")
        self.assertEqual(chat.options["max_tokens"], 8192)

    def test_unknown_citation_is_removed_and_reported(self):
        chat = FakeChatBackend("正确结论。[E1] 另一结论。[E99]")
        result = PhysicsExperimentAssistant(FakeRetriever([self.hit]), chat).ask("问题")
        self.assertNotIn("[E1]", result.answer)
        self.assertNotIn("[E99]", result.answer)
        self.assertTrue(result.grounded)
        self.assertEqual([item.evidence_id for item in result.citations], ["E1"])
        self.assertTrue(any("E99" in warning for warning in result.warnings))

    def test_answer_without_inline_citation_is_accepted(self):
        chat = FakeChatBackend("这是一个没有引用的答案。")
        result = PhysicsExperimentAssistant(FakeRetriever([self.hit]), chat).ask("问题")
        self.assertTrue(result.grounded)
        self.assertEqual([item.evidence_id for item in result.citations], ["E1"])
        self.assertEqual(result.answer, "这是一个没有引用的答案。")

    def test_no_evidence_uses_general_knowledge_with_upload_notice(self):
        chat = FakeChatBackend("可以通过增加重复测量次数降低随机误差。")
        result = PhysicsExperimentAssistant(FakeRetriever([]), chat).ask("未知问题")
        self.assertEqual(chat.calls, 1)
        self.assertFalse(result.grounded)
        self.assertIn("覆盖有限", result.answer)
        self.assertIn("上传相关实验资料", result.answer)
        self.assertTrue(result.answer.endswith("降低随机误差。"))

    def test_empty_question_skips_retrieval_and_generation(self):
        retriever = FakeRetriever([self.hit])
        chat = FakeChatBackend("不应被调用")
        result = PhysicsExperimentAssistant(retriever, chat).ask("  ")
        self.assertEqual(retriever.calls, 0)
        self.assertEqual(chat.calls, 0)
        self.assertIn("问题为空", result.warnings)

    def test_optional_score_threshold_can_trigger_refusal(self):
        low_score_hit = make_hit("low", "可能相关。", score=0.01)
        chat = FakeChatBackend("这是通用知识回答。")
        assistant = PhysicsExperimentAssistant(
            FakeRetriever([low_score_hit]), chat,
            AssistantConfig(minimum_retrieval_score=0.1),
        )
        result = assistant.ask("问题")
        self.assertFalse(result.grounded)
        self.assertEqual(chat.calls, 1)
        self.assertIn("上传相关实验资料", result.answer)

    def test_partial_material_does_not_show_coverage_notice(self):
        chat = FakeChatBackend("可以先检查仪器零点，再增加重复测量次数。")
        result = PhysicsExperimentAssistant(FakeRetriever([self.hit]), chat).ask("问题")
        self.assertTrue(result.grounded)
        self.assertNotIn("覆盖有限", result.answer)
        self.assertNotIn("上传相关实验资料", result.answer)

    def test_rewritten_question_is_used_only_for_retrieval(self):
        retriever = FakeRetriever([self.hit])
        chat = FakeChatBackend("结论有证据支持。[E1]")
        history = [{"role": "user", "content": "杨氏模量实验怎么做？"}]
        assistant = PhysicsExperimentAssistant(
            retriever, chat, question_rewriter=FixedQuestionRewriter(),
        )
        result = assistant.ask("那不确定度呢？", conversation_history=history)

        self.assertEqual(retriever.last_question, "杨氏模量实验的不确定度如何计算？")
        self.assertTrue(result.history_rewrite_used)
        self.assertIn("学生当前问题：\n那不确定度呢？", chat.messages[1]["content"])
        self.assertIn("<conversation_history>", chat.messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
