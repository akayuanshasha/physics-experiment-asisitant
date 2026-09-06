"""Independent online retrieval core for the physics-experiment RAG system."""

from .assistant import AnswerResult, AssistantConfig, PhysicsExperimentAssistant
from .chat import ChatBackend, ChatConfig, ChatServiceError, RemoteChatBackend
from .context import ContextConfig, ContextPackage, Evidence, build_context
from .cache import EmbeddingCache, EmbeddingCacheError, QueryEmbeddingCache
from .corpus import load_corpus
from .embeddings import (
    BM25OnlyEmbeddingBackend,
    EmbeddingBackend,
    EmbeddingConfig,
    EmbeddingServiceError,
    LocalEmbeddingConfig,
    LocalSentenceTransformerBackend,
    RemoteEmbeddingBackend,
    validate_embedding_batch,
)
from .factory import create_assistant_from_env
from .history import HistoryQuestionRewriter, RewriteResult
from .models import Chunk, RetrievalHit, RetrievalResult
from .parsed_document import ParsedBlock, ParsedDocument, ParsedPage
from .quality import QualityGateResult, evaluate_rag_markdown
from .retriever import HybridRetriever, RetrievalConfig
from .reranker import CrossEncoderReranker, Reranker
from .session_store import (
    RedisSessionStore,
    SessionStore,
    SQLiteSessionStore,
    create_session_store_from_env,
)
from .user_corpus import (
    MAX_USER_CORPUS_FILE_BYTES,
    MAX_USER_CORPUS_PDF_PAGES,
    UserCorpusValidationError,
    load_user_corpus,
    validate_user_corpus_file,
)
from .diagnostics import RagDiagnostics, anonymous_id

__all__ = [
    "AnswerResult",
    "AssistantConfig",
    "ChatBackend",
    "ChatConfig",
    "ChatServiceError",
    "BM25OnlyEmbeddingBackend",
    "Chunk",
    "ContextConfig",
    "ContextPackage",
    "CrossEncoderReranker",
    "EmbeddingBackend",
    "EmbeddingCache",
    "EmbeddingCacheError",
    "EmbeddingConfig",
    "EmbeddingServiceError",
    "LocalEmbeddingConfig",
    "LocalSentenceTransformerBackend",
    "HybridRetriever",
    "HistoryQuestionRewriter",
    "Evidence",
    "PhysicsExperimentAssistant",
    "ParsedBlock",
    "ParsedDocument",
    "ParsedPage",
    "RemoteEmbeddingBackend",
    "RemoteChatBackend",
    "RetrievalConfig",
    "RetrievalHit",
    "RetrievalResult",
    "Reranker",
    "RagDiagnostics",
    "RedisSessionStore",
    "SessionStore",
    "SQLiteSessionStore",
    "RewriteResult",
    "QualityGateResult",
    "QueryEmbeddingCache",
    "build_context",
    "anonymous_id",
    "create_assistant_from_env",
    "evaluate_rag_markdown",
    "create_session_store_from_env",
    "load_user_corpus",
    "validate_user_corpus_file",
    "UserCorpusValidationError",
    "MAX_USER_CORPUS_FILE_BYTES",
    "MAX_USER_CORPUS_PDF_PAGES",
    "load_corpus",
    "validate_embedding_batch",
]
