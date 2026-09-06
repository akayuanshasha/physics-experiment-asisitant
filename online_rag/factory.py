"""Convenience construction for the complete environment-configured pipeline."""

from __future__ import annotations

import os
from dataclasses import replace

from .assistant import AssistantConfig, PhysicsExperimentAssistant
from .chat import ChatConfig, RemoteChatBackend
from .embeddings import (
    BM25OnlyEmbeddingBackend,
    EmbeddingConfig,
    LocalEmbeddingConfig,
    LocalSentenceTransformerBackend,
    RemoteEmbeddingBackend,
)
from .history import HistoryQuestionRewriter
from .prompts import build_upload_context_block
from .retriever import HybridRetriever, RetrievalConfig
from .reranker import CrossEncoderReranker
from .corpus import corpus_source_hashes, load_corpus
from .user_corpus import load_user_corpus


def _optional_float(name: str, default: float) -> float | None:
    value = os.getenv(name, str(default)).strip().lower()
    if value in {"", "none", "off", "disabled"}:
        return None
    return float(value)


def _embedding_backend_from_env(
    embedding_config: EmbeddingConfig | None,
    retrieval_config: RetrievalConfig,
):
    """Resolve remote/local/BM25 mode without making a network request."""
    mode = os.getenv("RAG_EMBEDDING_BACKEND", "auto").strip().lower() or "auto"
    if mode not in {"auto", "remote", "local", "bm25"}:
        raise ValueError("RAG_EMBEDDING_BACKEND 必须是 auto、remote、local 或 bm25")

    local_model = os.getenv("LOCAL_EMBEDDING_MODEL", "").strip()
    remote_configured = bool(
        embedding_config is not None or os.getenv("EMBEDDING_MODEL", "").strip()
    )
    if mode == "local" or (mode == "auto" and local_model):
        return LocalSentenceTransformerBackend(LocalEmbeddingConfig.from_env()), retrieval_config
    if mode == "remote" or (mode == "auto" and remote_configured):
        resolved = embedding_config or EmbeddingConfig.from_env()
        return RemoteEmbeddingBackend(resolved), retrieval_config
    return BM25OnlyEmbeddingBackend(), replace(retrieval_config, dense_weight=0.0)


def create_assistant_from_env(
    *,
    embedding_config: EmbeddingConfig | None = None,
    chat_config: ChatConfig | None = None,
    retrieval_config: RetrievalConfig | None = None,
    assistant_config: AssistantConfig | None = None,
    user_corpus_root: str | None = None,
    user_id: str | None = None,
) -> PhysicsExperimentAssistant:
    """Build the online RAG assistant; the first call may populate vector cache."""
    resolved_chat_config = chat_config or ChatConfig.from_env()
    resolved_assistant_config = assistant_config or AssistantConfig(
        minimum_retrieval_score=_optional_float("RAG_MIN_RRF_SCORE", 0.03),
        minimum_bm25_score=_optional_float("RAG_MIN_BM25_SCORE", 50.0),
    )
    chat_backend = RemoteChatBackend(resolved_chat_config)
    reranker_model = os.getenv("RERANKER_MODEL", "").strip()
    reranker = CrossEncoderReranker(reranker_model) if reranker_model else None
    resolved_retrieval_config = retrieval_config or RetrievalConfig.from_env()
    if retrieval_config is None:
        resolved_retrieval_config = replace(
            resolved_retrieval_config,
            primary_minimum_retrieval_score=(
                resolved_assistant_config.minimum_retrieval_score or 0.0
            ),
            primary_minimum_bm25_score=(
                resolved_assistant_config.minimum_bm25_score or 0.0
            ),
        )
    embedding_backend, resolved_retrieval_config = _embedding_backend_from_env(
        embedding_config, resolved_retrieval_config,
    )
    extra_chunks = []
    duplicate_chunks = []
    user_corpus_warnings: list[str] = []
    if user_corpus_root and user_id:
        system_content_hashes = corpus_source_hashes(
            resolved_retrieval_config.corpus_root,
        )
        extra_chunks = load_user_corpus(
            user_corpus_root,
            user_id,
            target_chars=resolved_retrieval_config.chunk_target_chars,
            max_chars=resolved_retrieval_config.chunk_max_chars,
            overlap_chars=resolved_retrieval_config.chunk_overlap_chars,
            warnings=user_corpus_warnings,
            excluded_content_hashes=system_content_hashes,
            duplicate_chunks=duplicate_chunks,
        )
    # 与系统语料重复的上传不重复索引，但助教仍要知道它的存在：
    # 文件清单照列，提问该资料时按上传原文直接注入。
    upload_chunks = extra_chunks + duplicate_chunks
    retriever = HybridRetriever.from_corpus(
        embedding_backend,
        resolved_retrieval_config,
        reranker=reranker,
        extra_chunks=extra_chunks,
    )
    return PhysicsExperimentAssistant(
        retriever,
        chat_backend,
        resolved_assistant_config,
        question_rewriter=HistoryQuestionRewriter(chat_backend),
        startup_warnings=user_corpus_warnings,
        user_upload_context=build_upload_context_block(upload_chunks),
        user_upload_chunks=upload_chunks,
    )
