"""Orchestrate retrieval, context construction, generation and source tracking."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Protocol

from .chat import ChatBackend, ChatServiceError
from .context import ContextConfig, ContextPackage, Evidence, build_context
from .history import HistoryQuestionRewriter
from .models import Chunk, RetrievalHit, RetrievalResult
from .prompts import NO_EVIDENCE_NOTICE, build_messages


_CITATION_RE = re.compile(r"\[(E\d+)\]", re.I)
# 明确指向学生上传资料的提问用语；命中时跳过检索、直接注入上传内容。
_UPLOAD_REFERRING_TERMS = (
    "上传的资料", "上传资料", "这个资料", "这份资料", "这些资料", "那些资料",
    "这个文档", "这份文档", "这些文档", "这个文件", "这份文件", "这些文件",
    "我传的", "我上传", "上传的", "刚上传", "刚才上传",
    "我的讲义", "我的笔记", "我的资料", "我的文档",
    "资料讲了", "资料讲的是", "文档讲了", "文档讲的是", "文件讲了", "讲义讲了",
    "它讲的是什么", "它讲了什么",
    "这个pdf", "这份pdf", "这些pdf", "这个ppt", "这份ppt",
    "这个doc", "这个word", "这份word",
)
# 指代性说法本身不锁定上传资料（“该实验怎么做”应正常检索），
# 只有同时询问内容（“这个实验讲的是什么”）才视为询问上传资料。
_UPLOAD_DEMO_TERMS = (
    "这个实验", "该实验", "这些实验",
    "这份指导书", "这个指导书", "该指导书", "这些指导书",
)
_UPLOAD_DOC_NOUNS = ("资料", "文档", "文件", "讲义", "笔记", "材料", "指导书")
_UPLOAD_CONTENT_ASKS = (
    "讲的是什么", "讲了什么", "讲什么", "讲了哪些", "讲了些什么",
    "主要内容", "内容是什么", "总结", "概括", "介绍", "写了什么", "说的是什么",
)


def _refers_to_uploaded_materials(question: str) -> bool:
    """判断问题是否在询问学生上传的资料本身（如“这个资料讲的是什么”）。"""
    text = str(question or "").strip()
    if not text:
        return False
    lowered = text.lower()
    for term in _UPLOAD_REFERRING_TERMS:
        if term in lowered:
            return True
    if any(term in text for term in _UPLOAD_DEMO_TERMS) and any(
        word in text for word in _UPLOAD_CONTENT_ASKS
    ):
        return True
    if not any(word in text for word in _UPLOAD_DOC_NOUNS):
        return False
    return any(word in text for word in _UPLOAD_CONTENT_ASKS)
_EMPTY_QUESTION_ANSWER = "请输入你想咨询的具体问题。"
_EVIDENCE_FOOTER_RE = re.compile(
    r"(?im)^\s*(?:实际使用的)?(?:证据编号|使用的证据编号|依据)\s*[:：]"
    r"\s*(?:\[E\d+\][,，、;；\s]*)+[。.]?\s*$"
)
_INVALID_GENERATION_ANSWER = "模型未能生成有效答案，请稍后重试。"


def _remove_evidence_artifacts(answer: str) -> str:
    """Remove internal evidence labels from user-visible answer text."""
    text = _EVIDENCE_FOOTER_RE.sub("", answer or "")
    text = _CITATION_RE.sub("", text)
    text = re.sub(r"[ \t]+([，。；：！？,.!?])", r"\1", text)
    return re.sub(r"\n{3,}", "\n\n", text)


def _clean_user_visible_answer(answer: str) -> str:
    return _remove_evidence_artifacts(answer).strip()


class RetrieverLike(Protocol):
    def retrieve(self, question: str, top_k: int = 6) -> RetrievalResult: ...


@dataclass(frozen=True)
class AssistantConfig:
    retrieval_top_k: int = 12
    context: ContextConfig = field(default_factory=ContextConfig)
    temperature: float = 0.1
    max_output_tokens: int = 8192
    minimum_retrieval_score: float | None = 0.03
    minimum_bm25_score: float | None = 50.0
    require_citations: bool = False
    adjacent_context_chunks: int = 1
    primary_hits_before_neighbors: int = 3


@dataclass
class AnswerResult:
    question: str
    answer: str
    citations: list[Evidence]
    evidence: list[Evidence]
    retrieval: RetrievalResult
    grounded: bool
    warnings: list[str] = field(default_factory=list)
    timings_ms: dict[str, float] = field(default_factory=dict)
    retrieval_question: str = ""
    history_rewrite_used: bool = False
    generation_mode: str = ""
    fallback_used: bool = False
    proxy_mode: str = ""
    retrieval_diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "evidence": [item.to_dict() for item in self.evidence],
            "retrieval": self.retrieval.to_dict(),
            "grounded": self.grounded,
            "warnings": list(self.warnings),
            "timings_ms": dict(self.timings_ms),
            "retrieval_question": self.retrieval_question or self.question,
            "history_rewrite_used": self.history_rewrite_used,
            "generation_mode": self.generation_mode,
            "fallback_used": self.fallback_used,
            "proxy_mode": self.proxy_mode,
            "retrieval_diagnostics": dict(self.retrieval_diagnostics),
        }


def _empty_retrieval(question: str) -> RetrievalResult:
    return RetrievalResult(question, "", [], [])


def _upload_context_config(config: ContextConfig) -> ContextConfig:
    """注入上传资料时放宽证据上限，避免整份文件被每实验上限截断。"""
    return replace(
        config,
        max_evidence=24,
        max_chunks_per_experiment=24,
        max_context_chars=12000,
    )


def _upload_hits(chunks: Iterable[Chunk]) -> list[RetrievalHit]:
    return [RetrievalHit(chunk=chunk, score=0.0) for chunk in chunks]


def _citation_ids(answer: str) -> list[str]:
    found: list[str] = []
    for match in _CITATION_RE.finditer(answer):
        value = match.group(1).upper()
        if value not in found:
            found.append(value)
    return found


@dataclass
class _PreparedAnswer:
    started: float
    question: str
    retrieval_question: str
    history_rewrite_used: bool
    retrieval: RetrievalResult
    context: ContextPackage
    warnings: list[str]
    retrieval_ms: float
    messages: list[dict[str, str]]
    retrieval_diagnostics: dict[str, Any]
    general_knowledge_fallback: bool = False


def _dense_fallback_reason(retrieval: RetrievalResult) -> str | None:
    """Return a non-sensitive failure category for structured diagnostics."""

    if retrieval.retrieval_mode != "bm25_fallback":
        return None
    for warning in retrieval.warnings:
        match = re.search(r"\b([A-Za-z][A-Za-z0-9_]*(?:Error|Exception))\b", warning)
        if match:
            return match.group(1)
        if "超时" in warning:
            return "timeout"
    return "dense_unavailable"


class PhysicsExperimentAssistant:
    def __init__(
        self,
        retriever: RetrieverLike,
        chat_backend: ChatBackend,
        config: AssistantConfig | None = None,
        question_rewriter: HistoryQuestionRewriter | None = None,
        startup_warnings: Iterable[str] = (),
        user_upload_context: str = "",
        user_upload_chunks: Iterable[Chunk] = (),
    ):
        self.retriever = retriever
        self.chat_backend = chat_backend
        self.config = config or AssistantConfig()
        self.question_rewriter = question_rewriter
        self.startup_warnings = [str(item) for item in startup_warnings if str(item)]
        self.user_upload_context = user_upload_context or ""
        self.user_upload_chunks = tuple(user_upload_chunks)

    def _prepare(
        self,
        question: str,
        *,
        experiment_ids: Iterable[str] | None = None,
        conversation_history: list[dict] | None = None,
    ) -> _PreparedAnswer | AnswerResult:
        started = time.perf_counter()
        question = str(question or "").strip()
        if not question:
            return AnswerResult(
                question="", answer=_EMPTY_QUESTION_ANSWER, citations=[], evidence=[],
                retrieval=_empty_retrieval(""), grounded=False,
                warnings=["问题为空"],
                timings_ms={"total": (time.perf_counter() - started) * 1000},
            )

        retrieval_question = question
        history_rewrite_used = False
        rewrite_warning: str | None = None
        if self.question_rewriter is not None:
            rewrite = self.question_rewriter.rewrite(question, conversation_history)
            retrieval_question = rewrite.question
            history_rewrite_used = rewrite.rewritten
            rewrite_warning = rewrite.warning

        retrieval_started = time.perf_counter()
        upload_intent = bool(self.user_upload_chunks) and (
            _refers_to_uploaded_materials(question)
            or _refers_to_uploaded_materials(retrieval_question)
        )
        if upload_intent:
            # 问题明确指向学生上传资料：跳过检索，直接把上传内容按证据格式注入。
            retrieval = RetrievalResult(retrieval_question, "", [], [])
            context = build_context(
                _upload_hits(self.user_upload_chunks),
                _upload_context_config(self.config.context),
            )
            retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
            retrieval_diagnostics = {
                "query_variant_count": 0,
                "retrieved_count": 0,
                "eligible_count": 0,
                "filtered_count": 0,
                "maximum_lexical_score": 0.0,
                "dense_fallback_reason": None,
                "upload_intent_injection": True,
                "upload_fallback_injection": False,
            }
            warnings = list(self.startup_warnings) + list(context.warnings)
            if context.evidence:
                warnings.append("问题指向学生上传资料，已直接注入上传资料内容")
        else:
            page_context = [
                str(experiment_id).strip()
                for experiment_id in (experiment_ids or [])
                if str(experiment_id).strip()
            ]
            if page_context:
                retrieval = self.retriever.retrieve(
                    retrieval_question,
                    top_k=self.config.retrieval_top_k,
                    experiment_ids=page_context,
                )
            else:
                retrieval = self.retriever.retrieve(
                    retrieval_question, top_k=self.config.retrieval_top_k,
                )
            retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
            eligible_hits = retrieval.hits
            filtering_warnings: list[str] = []
            threshold = self.config.minimum_retrieval_score
            if threshold is not None:
                eligible_hits = [hit for hit in eligible_hits if hit.score >= threshold]
            bm25_threshold = self.config.minimum_bm25_score
            if bm25_threshold is not None and retrieval.retrieval_mode in {
                "bm25", "bm25_fallback",
            }:
                eligible_hits = [
                    hit for hit in eligible_hits
                    if hit.lexical_score >= bm25_threshold
                ]
            filtered_count = len(retrieval.hits) - len(eligible_hits)
            if filtered_count:
                filtering_warnings.append(
                    f"最低相关性门槛过滤了 {filtered_count} 条候选"
                )

            context_hits = eligible_hits
            expand_context = getattr(self.retriever, "expand_context", None)
            if callable(expand_context):
                context_hits = expand_context(
                    eligible_hits,
                    neighbors=self.config.adjacent_context_chunks,
                    primary_limit=self.config.primary_hits_before_neighbors,
                )
            upload_fallback_used = False
            if context_hits:
                context = build_context(context_hits, self.config.context)
            elif self.user_upload_chunks:
                # 检索没有找到可用资料：优先改用学生上传的资料回答，
                # 使“这个实验讲的是什么”等检索不到的元问题也能落在上传内容上。
                upload_fallback_used = True
                context = build_context(
                    _upload_hits(self.user_upload_chunks),
                    _upload_context_config(self.config.context),
                )
                filtering_warnings.append(
                    "检索未找到可用资料，已改用学生上传的资料回答"
                )
            else:
                context = build_context(context_hits, self.config.context)
            retrieval_diagnostics = {
                "query_variant_count": len(retrieval.query_variants),
                "retrieved_count": len(retrieval.hits),
                "eligible_count": len(eligible_hits),
                "filtered_count": filtered_count,
                "maximum_lexical_score": max(
                    (hit.lexical_score for hit in retrieval.hits), default=0.0,
                ),
                "dense_fallback_reason": _dense_fallback_reason(retrieval),
                "upload_intent_injection": False,
                "upload_fallback_injection": upload_fallback_used,
            }
            warnings = (
                list(self.startup_warnings) + list(retrieval.warnings)
                + filtering_warnings + list(context.warnings)
            )
        if rewrite_warning:
            warnings.insert(0, rewrite_warning)
        general_knowledge_fallback = not context.evidence
        if general_knowledge_fallback:
            warnings.append("没有足够的可用检索证据，已回退到通用知识回答")

        messages = build_messages(
            question,
            context,
            conversation_history,
            upload_context=self.user_upload_context,
        )
        return _PreparedAnswer(
            started=started,
            question=question,
            retrieval_question=retrieval_question,
            history_rewrite_used=history_rewrite_used,
            retrieval=retrieval,
            context=context,
            warnings=warnings,
            retrieval_ms=retrieval_ms,
            messages=messages,
            retrieval_diagnostics=retrieval_diagnostics,
            general_knowledge_fallback=general_knowledge_fallback,
        )

    def _finalize(
        self,
        prepared: _PreparedAnswer,
        answer: str,
        generation_ms: float,
        *,
        generation_mode: str = "nonstream",
        fallback_used: bool = False,
    ) -> AnswerResult:
        raw_answer = answer.strip()
        warnings = list(prepared.warnings)
        context = prepared.context
        retrieval = prepared.retrieval
        available = {item.evidence_id: item for item in context.evidence}
        requested_ids = _citation_ids(raw_answer)
        unknown_ids = [item for item in requested_ids if item not in available]
        if unknown_ids:
            warnings.append("模型引用了不存在的证据编号：" + ", ".join(unknown_ids))

        answer = _clean_user_visible_answer(raw_answer)
        citations = list(context.evidence)
        if not answer:
            warnings.append("生成模型返回了空答案")
            answer = _INVALID_GENERATION_ANSWER
            citations = []
        elif prepared.general_knowledge_fallback:
            answer = NO_EVIDENCE_NOTICE + "\n\n" + answer

        grounded = bool(citations)
        return AnswerResult(
            question=prepared.question,
            answer=answer,
            citations=citations,
            evidence=list(context.evidence),
            retrieval=retrieval,
            grounded=grounded,
            warnings=warnings,
            timings_ms={
                "retrieval": prepared.retrieval_ms,
                "generation": generation_ms,
                "total": (time.perf_counter() - prepared.started) * 1000,
            },
            retrieval_question=prepared.retrieval_question,
            history_rewrite_used=prepared.history_rewrite_used,
            generation_mode=generation_mode,
            fallback_used=fallback_used,
            proxy_mode=getattr(
                getattr(self.chat_backend, "config", None), "proxy_mode", "",
            ),
            retrieval_diagnostics=dict(prepared.retrieval_diagnostics),
        )

    def ask(
        self,
        question: str,
        *,
        experiment_ids: Iterable[str] | None = None,
        conversation_history: list[dict] | None = None,
    ) -> AnswerResult:
        prepared = self._prepare(
            question,
            experiment_ids=experiment_ids,
            conversation_history=conversation_history,
        )
        if isinstance(prepared, AnswerResult):
            return prepared
        generation_started = time.perf_counter()
        answer = self.chat_backend.complete(
            prepared.messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
        )
        generation_ms = (time.perf_counter() - generation_started) * 1000
        return self._finalize(prepared, answer, generation_ms)

    def ask_stream(
        self,
        question: str,
        *,
        experiment_ids: Iterable[str] | None = None,
        conversation_history: list[dict] | None = None,
    ):
        """Yield meta/token/done dictionaries; done contains a validated AnswerResult."""
        prepared = self._prepare(
            question,
            experiment_ids=experiment_ids,
            conversation_history=conversation_history,
        )
        if isinstance(prepared, AnswerResult):
            yield {"type": "done", "result": prepared}
            return
        yield {
            "type": "meta",
            "retrieval_mode": prepared.retrieval.retrieval_mode,
            "retrieved_count": len(prepared.retrieval.hits),
            "evidence_count": len(prepared.context.evidence),
            "retrieval_ms": prepared.retrieval_ms,
        }
        generation_started = time.perf_counter()
        pieces: list[str] = []
        visible_tail = ""
        visible_emitted = False
        notice_emitted = False
        fallback_used = False
        generation_mode = "stream"
        stream_holdback = 128

        def user_visible_piece(text: str) -> str:
            nonlocal notice_emitted
            if not text:
                return ""
            if prepared.general_knowledge_fallback and not notice_emitted:
                notice_emitted = True
                return NO_EVIDENCE_NOTICE + "\n\n" + text
            return text

        stream_complete = getattr(self.chat_backend, "stream_complete", None)
        if callable(stream_complete):
            try:
                for piece in stream_complete(
                    prepared.messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_output_tokens,
                ):
                    if piece:
                        pieces.append(piece)
                        visible_tail += piece
                        if len(visible_tail) > stream_holdback:
                            split_at = len(visible_tail) - stream_holdback
                            marker_start = visible_tail.rfind(
                                "[", max(0, split_at - 8), split_at,
                            )
                            if marker_start >= 0:
                                split_at = marker_start
                            ready = visible_tail[:split_at]
                            visible_tail = visible_tail[split_at:]
                            cleaned = user_visible_piece(
                                _remove_evidence_artifacts(ready)
                            )
                            if cleaned:
                                visible_emitted = True
                                yield {"type": "token", "text": cleaned}
            except ChatServiceError:
                if visible_emitted:
                    raise
                fallback_used = True
                generation_mode = "nonstream_fallback"
                prepared.warnings.append("流式生成失败，已自动使用非流式回答")
                piece = self.chat_backend.complete(
                    prepared.messages,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_output_tokens,
                )
                pieces = [piece]
                visible_tail = piece
        else:
            generation_mode = "nonstream"
            piece = self.chat_backend.complete(
                prepared.messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_output_tokens,
            )
            pieces.append(piece)
            visible_tail = piece
        cleaned_tail = user_visible_piece(_clean_user_visible_answer(visible_tail))
        if cleaned_tail:
            visible_emitted = True
            yield {"type": "token", "text": cleaned_tail}
        generation_ms = (time.perf_counter() - generation_started) * 1000
        yield {
            "type": "done",
            "result": self._finalize(
                prepared,
                "".join(pieces),
                generation_ms,
                generation_mode=generation_mode,
                fallback_used=fallback_used,
            ),
        }

    def close(self) -> None:
        """Release resources owned by this per-user assistant instance."""
        embedding_backend = getattr(self.retriever, "embedding_backend", None)
        close = getattr(embedding_backend, "close", None)
        if callable(close):
            close()
