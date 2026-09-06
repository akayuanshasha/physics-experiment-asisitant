"""Multi-query BM25 + dense retrieval fused with weighted RRF."""

from __future__ import annotations

from collections import OrderedDict
import hashlib
import math
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from query_aliases import (
    build_query_variants,
    normalize_query,
    should_include_related_expansions,
)

from .cache import QueryEmbeddingCache
from .corpus import load_corpus
from .embeddings import (
    EmbeddingBackend,
    EmbeddingCache,
    EmbeddingCacheError,
    EmbeddingServiceError,
    cosine_similarity,
    normalize_vector,
    validate_embedding_batch,
)
from .lexical import BM25Index
from .models import Chunk, RetrievalHit, RetrievalResult
from .reranker import Reranker


def _embedding_cache_namespace(backend: EmbeddingBackend) -> str:
    try:
        value = getattr(backend, "cache_namespace", None)
    except Exception:
        value = None
    if not value:
        try:
            value = getattr(backend, "model_name")
        except Exception:
            value = type(backend).__name__
    return str(value)


_SECRET_VALUE_RE = re.compile(
    r"(?:bearer\s+|(?:sk|api[_-]?key)[=:_-]?)[A-Za-z0-9._~+/=-]{8,}",
    re.IGNORECASE,
)


def _safe_embedding_error(exc: Exception) -> str:
    detail = _SECRET_VALUE_RE.sub("[REDACTED]", str(exc or ""))[:500]
    return f"{type(exc).__name__}: {detail}" if detail else type(exc).__name__


@dataclass(frozen=True)
class RetrievalConfig:
    corpus_root: str | Path = "b_static/experiment"
    cache_path: str | Path = ".cache/online_rag/embeddings.sqlite3"
    chunk_target_chars: int = 700
    chunk_max_chars: int = 1000
    chunk_overlap_chars: int = 100
    candidate_k: int = 20
    max_query_variants: int = 8
    rrf_k: int = 60
    lexical_weight: float = 1.0
    dense_weight: float = 1.0
    dense_score_threshold: float = 0.25
    document_embedding_batch_size: int = 8
    experiment_title_boost: float = 0.01
    user_upload_boost: float = 0.01
    page_context_boost: float = 0.012
    strict_page_context: bool = False
    section_intent_boost: float = 0.004
    template_section_penalty: float = 0.002
    supplementary_reference_penalty: float = 0.007
    primary_minimum_retrieval_score: float = 0.03
    primary_minimum_bm25_score: float = 50.0
    max_hits_per_source_first_pass: int = 2
    allow_bm25_fallback: bool = True
    rerank_candidate_k: int = 20
    cache_busy_timeout_ms: int = 15000
    cache_migrate_legacy: bool = True
    query_cache_size: int = 256
    query_cache_ttl_seconds: float = 300.0
    query_cache_wait_timeout_seconds: float = 120.0
    query_cache_path: str | Path | None = None
    query_cache_max_entries: int = 4096
    query_cache_failure_cooldown_seconds: float = 30.0
    query_cache_maintenance_interval_seconds: float = 60.0
    query_cache_cross_process_wait_timeout_seconds: float = 30.0
    query_cache_lease_seconds: float = 120.0
    document_build_lock_timeout_seconds: float = 300.0
    cache_namespace_max_age_seconds: float | None = None
    cache_checkpoint_mode: str = "PASSIVE"
    cache_maintenance_vacuum: bool = False
    use_vectorized_dense_search: bool = True
    dense_recovery_cooldown_seconds: float = 30.0

    @classmethod
    def from_env(cls, base: "RetrievalConfig | None" = None) -> "RetrievalConfig":
        """Apply only cache and dense-recovery deployment settings."""
        current = base or cls()

        def integer(name: str, default: int, minimum: int = 0) -> int:
            raw = os.getenv(name, str(default)).strip()
            try:
                value = int(raw)
            except ValueError as exc:
                raise ValueError(f"{name} 必须是整数") from exc
            if value < minimum:
                raise ValueError(f"{name} 必须大于或等于 {minimum}")
            return value

        def number(name: str, default: float, minimum: float = 0.0) -> float:
            raw = os.getenv(name, str(default)).strip()
            try:
                value = float(raw)
            except ValueError as exc:
                raise ValueError(f"{name} 必须是数字") from exc
            if not math.isfinite(value) or value < minimum:
                raise ValueError(f"{name} 必须大于或等于 {minimum}")
            return value

        def boolean(name: str, default: bool) -> bool:
            raw = os.getenv(name, "1" if default else "0").strip().lower()
            if raw in {"1", "true", "yes", "on"}:
                return True
            if raw in {"0", "false", "no", "off"}:
                return False
            raise ValueError(f"{name} 必须是 0/1 或 true/false")

        cache_path = os.getenv("RAG_EMBEDDING_CACHE", "").strip() or current.cache_path
        query_path = os.getenv("RAG_QUERY_CACHE_PATH", "").strip()
        namespace_age = os.getenv("RAG_CACHE_NAMESPACE_MAX_AGE_SECONDS", "").strip()
        checkpoint_mode = (
            os.getenv("RAG_CACHE_CHECKPOINT_MODE", current.cache_checkpoint_mode).strip().upper()
            or current.cache_checkpoint_mode
        )
        if checkpoint_mode not in {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}:
            raise ValueError("RAG_CACHE_CHECKPOINT_MODE 配置无效")
        return replace(
            current,
            cache_path=cache_path,
            cache_busy_timeout_ms=integer(
                "RAG_CACHE_BUSY_TIMEOUT_MS", current.cache_busy_timeout_ms, 100,
            ),
            cache_migrate_legacy=boolean(
                "RAG_CACHE_MIGRATE_LEGACY", current.cache_migrate_legacy,
            ),
            query_cache_size=integer("RAG_QUERY_CACHE_SIZE", current.query_cache_size, 0),
            query_cache_ttl_seconds=number(
                "RAG_QUERY_CACHE_TTL_SECONDS", current.query_cache_ttl_seconds,
            ),
            query_cache_wait_timeout_seconds=number(
                "RAG_QUERY_CACHE_WAIT_TIMEOUT_SECONDS",
                current.query_cache_wait_timeout_seconds,
            ),
            query_cache_path=(query_path or current.query_cache_path),
            query_cache_max_entries=integer(
                "RAG_QUERY_CACHE_MAX_ENTRIES", current.query_cache_max_entries, 1,
            ),
            query_cache_failure_cooldown_seconds=number(
                "RAG_QUERY_CACHE_FAILURE_COOLDOWN_SECONDS",
                current.query_cache_failure_cooldown_seconds,
            ),
            query_cache_maintenance_interval_seconds=number(
                "RAG_QUERY_CACHE_MAINTENANCE_INTERVAL_SECONDS",
                current.query_cache_maintenance_interval_seconds,
            ),
            query_cache_cross_process_wait_timeout_seconds=number(
                "RAG_QUERY_CACHE_CROSS_PROCESS_WAIT_TIMEOUT_SECONDS",
                current.query_cache_cross_process_wait_timeout_seconds,
            ),
            query_cache_lease_seconds=number(
                "RAG_QUERY_CACHE_LEASE_SECONDS", current.query_cache_lease_seconds,
            ),
            document_build_lock_timeout_seconds=number(
                "RAG_DOCUMENT_BUILD_LOCK_TIMEOUT_SECONDS",
                current.document_build_lock_timeout_seconds,
            ),
            cache_namespace_max_age_seconds=(
                number("RAG_CACHE_NAMESPACE_MAX_AGE_SECONDS", 0.0)
                if namespace_age else current.cache_namespace_max_age_seconds
            ),
            cache_checkpoint_mode=checkpoint_mode,
            cache_maintenance_vacuum=boolean(
                "RAG_CACHE_MAINTENANCE_VACUUM", current.cache_maintenance_vacuum,
            ),
            use_vectorized_dense_search=boolean(
                "RAG_USE_VECTORIZED_DENSE_SEARCH", current.use_vectorized_dense_search,
            ),
            dense_recovery_cooldown_seconds=number(
                "RAG_DENSE_RECOVERY_COOLDOWN_SECONDS",
                current.dense_recovery_cooldown_seconds,
            ),
            user_upload_boost=number(
                "RAG_USER_UPLOAD_BOOST", current.user_upload_boost,
            ),
        )


_DOCUMENT_BUILD_LOCKS: dict[str, threading.RLock] = {}
_DOCUMENT_BUILD_LOCKS_GUARD = threading.Lock()


def _document_build_lock(path: str | Path, model_name: str) -> threading.RLock:
    key = f"{Path(path).resolve()}\0{model_name}"
    with _DOCUMENT_BUILD_LOCKS_GUARD:
        return _DOCUMENT_BUILD_LOCKS.setdefault(key, threading.RLock())


class _DocumentBuildGuard:
    def __init__(
        self, thread_lock: threading.RLock, path: str | Path,
        model_name: str, timeout_seconds: float,
    ):
        self._thread_lock = thread_lock
        self._path = Path(path)
        self._model_name = model_name
        self._timeout_seconds = max(0.0, timeout_seconds)
        self._file_context = None
        self.file_locked = False

    def __enter__(self):
        self._thread_lock.acquire()
        lock_name = hashlib.sha256(self._model_name.encode("utf-8")).hexdigest()[:16]
        lock_path = Path(f"{self._path}.{lock_name}.build.lock")
        try:
            from .cache import _exclusive_file_lock

            self._file_context = _exclusive_file_lock(
                lock_path, timeout_seconds=self._timeout_seconds,
            )
            self._file_context.__enter__()
            self.file_locked = True
        except (EmbeddingCacheError, OSError):
            self._file_context = None
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._file_context is not None:
            self._file_context.__exit__(exc_type, exc_value, traceback)
        self._thread_lock.release()
        return False


def _document_build_guard(
    path: str | Path, model_name: str, timeout_seconds: float,
) -> _DocumentBuildGuard:
    return _DocumentBuildGuard(
        _document_build_lock(path, model_name), path, model_name, timeout_seconds,
    )


@dataclass
class _QueryFlight:
    model_name: str
    event: threading.Event = field(default_factory=threading.Event)
    result: list[float] | None = None
    error: Exception | None = None


class DenseVectorIndex:
    """Immutable dense index with strict dimensions and an optional NumPy path."""

    def __init__(
        self, vectors: list[list[float]], chunk_ids: list[str], *, use_numpy: bool = True,
    ):
        if len(vectors) != len(chunk_ids):
            raise EmbeddingServiceError("文档向量数量与语料块数量不一致")
        self.dimension = len(vectors[0]) if vectors else 0
        if any(not vector or len(vector) != self.dimension for vector in vectors):
            raise EmbeddingServiceError("文档向量索引维度不一致")
        self.vectors = vectors
        self.chunk_ids = chunk_ids
        self._matrix = None
        if use_numpy and vectors:
            try:
                import numpy as np

                matrix = np.asarray(vectors, dtype=np.float32)
                if matrix.ndim == 2 and matrix.shape == (len(vectors), self.dimension):
                    self._matrix = matrix
            except (ImportError, TypeError, ValueError):
                self._matrix = None

    @property
    def memory_bytes(self) -> int:
        if self._matrix is not None:
            return int(self._matrix.nbytes)
        return sum(len(vector) for vector in self.vectors) * 8

    def search(
        self, query_vector: list[float], *, threshold: float, limit: int,
    ) -> list[tuple[int, float]]:
        if not self.vectors or limit <= 0:
            return []
        if len(query_vector) != self.dimension:
            raise EmbeddingServiceError("查询向量与文档向量维度不一致")
        if self._matrix is not None:
            import numpy as np

            scores = self._matrix @ np.asarray(query_vector, dtype=np.float32)
            indices = np.flatnonzero(scores >= threshold)
            result = [(int(index), float(scores[index])) for index in indices]
        else:
            result = [
                (index, cosine_similarity(query_vector, vector))
                for index, vector in enumerate(self.vectors)
            ]
            result = [item for item in result if item[1] >= threshold]
        result.sort(key=lambda item: (-item[1], self.chunk_ids[item[0]]))
        return result[:limit]


class HybridRetriever:
    _SECTION_INTENTS = {
        "实验原理": ("原理", "为什么", "公式", "推导", "关系"),
        "实验仪器": ("仪器", "器材", "装置", "量程", "分度值"),
        "实验装置": ("装置", "仪器", "连接", "接线"),
        "实验内容": ("步骤", "操作", "怎么做", "流程", "调节"),
        "实验步骤": ("步骤", "操作", "怎么做", "流程", "调节"),
        "数据处理": ("数据", "计算", "处理", "拟合", "误差", "不确定度"),
        "数据记录": ("记录", "表格", "数据"),
        "注意事项": ("注意", "安全", "危险", "损坏", "错误操作"),
        "思考题": ("思考题", "讨论"),
    }
    _TEMPLATE_SECTIONS = ("实验要求", "注意事项", "实验报告")
    _EXAMPLE_INTENT_TERMS = (
        "示例", "样例", "范例", "演示", "模板", "怎么填", "如何填", "填写格式",
    )

    def __init__(
        self, chunks: list[Chunk], embedding_backend: EmbeddingBackend,
        config: RetrievalConfig | None = None,
        *, reranker: Reranker | None = None,
    ):
        self.config = config or RetrievalConfig()
        self.chunks = list(chunks)
        self.embedding_backend = embedding_backend
        self.reranker = reranker
        self._chunks_by_id = {chunk.chunk_id: chunk for chunk in self.chunks}
        self.lexical = BM25Index(self.chunks)
        self.dense_available = self.config.dense_weight > 0
        self.dense_error: str | None = None
        self.cache_warning: str | None = None
        self._document_model_name: str | None = None
        self.document_vectors: list[list[float]] = []
        self._dense_index: DenseVectorIndex | None = None
        self._query_cache: OrderedDict[str, tuple[float, list[float]]] = OrderedDict()
        self._query_cache_lock = threading.RLock()
        self._query_inflight: dict[str, _QueryFlight] = {}
        self._query_cache_hits = 0
        self._query_cache_misses = 0
        self._query_cache_waits = 0
        self._query_cache_persistent_hits = 0
        self._query_cache_persistent_misses = 0
        self._persistent_query_cache: QueryEmbeddingCache | None = None
        self._persistent_query_cache_model: str | None = None
        self._persistent_query_cache_error: str | None = None
        self._persistent_query_cache_disabled_until = 0.0
        self._persistent_query_cache_failures = 0
        self._document_state_lock = threading.RLock()
        self._dense_state_lock = threading.RLock()
        self._dense_recovery_lock = threading.Lock()
        self._dense_recovery_inflight = False
        self._dense_recovery_attempts = 0
        self._dense_recovery_successes = 0
        self._dense_recovery_next_at = 0.0
        self._dense_state_generation = 0
        self._maintenance_lock = threading.Lock()
        if self.dense_available:
            try:
                self.document_vectors = self._load_document_vectors()
            except Exception as exc:
                if not self.config.allow_bm25_fallback:
                    raise
                self._disable_dense(exc, "文档向量初始化")

    @classmethod
    def from_corpus(
        cls, embedding_backend: EmbeddingBackend,
        config: RetrievalConfig | None = None,
        *, reranker: Reranker | None = None,
        extra_chunks: Iterable[Chunk] = (),
    ) -> "HybridRetriever":
        cfg = config or RetrievalConfig()
        chunks = load_corpus(
            cfg.corpus_root, target_chars=cfg.chunk_target_chars,
            max_chars=cfg.chunk_max_chars, overlap_chars=cfg.chunk_overlap_chars,
        )
        chunks.extend(extra_chunks)
        return cls(chunks, embedding_backend, cfg, reranker=reranker)

    def _load_document_vectors(self) -> list[list[float]]:
        with self._document_state_lock:
            return self._load_document_vectors_unlocked()

    def _load_document_vectors_unlocked(self) -> list[list[float]]:
        for _ in range(3):
            model_name = _embedding_cache_namespace(self.embedding_backend)
            with _document_build_guard(
                self.config.cache_path, model_name,
                self.config.document_build_lock_timeout_seconds,
            ) as guard:
                if not guard.file_locked:
                    self.cache_warning = "无法取得跨进程文档构建锁，将继续在当前进程构建"
                if _embedding_cache_namespace(self.embedding_backend) != model_name:
                    continue
                cache: EmbeddingCache | None = None
                try:
                    cache = EmbeddingCache(
                        self.config.cache_path, model_name,
                        migrate_legacy=self.config.cache_migrate_legacy,
                        busy_timeout_ms=self.config.cache_busy_timeout_ms,
                    )
                except (EmbeddingCacheError, OSError, ValueError) as exc:
                    self.cache_warning = f"Embedding 缓存不可用，将仅使用内存索引：{exc}"

                texts = [chunk.embedding_text() for chunk in self.chunks]
                hashes = [hashlib.sha256(text.encode("utf-8")).hexdigest() for text in texts]
                keys = [
                    (chunk.chunk_id, text_hash)
                    for chunk, text_hash in zip(self.chunks, hashes)
                ]
                cached_values: dict[str, list[float]] = {}
                if cache is not None:
                    try:
                        cached_values = cache.get_many(keys)
                    except (EmbeddingCacheError, OSError, ValueError) as exc:
                        self.cache_warning = f"读取 Embedding 缓存失败，将重新计算：{exc}"
                        cache.close()
                        cache = None

                backend_dimension = getattr(self.embedding_backend, "dimension", None)
                expected_dimension = (
                    int(backend_dimension) if isinstance(backend_dimension, int)
                    and backend_dimension > 0 else None
                )
                vectors: list[list[float] | None] = [None] * len(self.chunks)
                missing_indices: list[int] = []
                for index, chunk in enumerate(self.chunks):
                    cached = cached_values.get(chunk.chunk_id)
                    if cached is not None:
                        try:
                            normalized = normalize_vector(cached)
                            if expected_dimension is None:
                                expected_dimension = len(normalized)
                            if len(normalized) == expected_dimension:
                                vectors[index] = normalized
                                continue
                        except EmbeddingServiceError:
                            pass
                    missing_indices.append(index)

                batch_size = max(1, self.config.document_embedding_batch_size)
                for start in range(0, len(missing_indices), batch_size):
                    batch_indices = missing_indices[start:start + batch_size]
                    batch_texts = [texts[index] for index in batch_indices]
                    embedded = self.embedding_backend.embed_documents(batch_texts)
                    if _embedding_cache_namespace(self.embedding_backend) != model_name:
                        break
                    normalized_batch = validate_embedding_batch(
                        embedded, len(batch_indices),
                        expected_dimension=expected_dimension,
                        context="文档 Embedding",
                    )
                    if normalized_batch and expected_dimension is None:
                        expected_dimension = len(normalized_batch[0])
                    to_cache = []
                    for index, normalized in zip(batch_indices, normalized_batch):
                        vectors[index] = normalized
                        to_cache.append((
                            self.chunks[index].chunk_id, hashes[index], normalized,
                        ))
                    if cache is not None and to_cache:
                        try:
                            cache.put_many(to_cache)
                            cache.save()
                        except (EmbeddingCacheError, OSError, ValueError) as exc:
                            self.cache_warning = f"写入 Embedding 缓存失败：{exc}"
                            cache.close()
                            cache = None
                else:
                    if any(vector is None for vector in vectors):
                        raise EmbeddingServiceError("部分文档未获得 Embedding 向量")
                    result = [vector for vector in vectors if vector is not None]
                    index = DenseVectorIndex(
                        result, [chunk.chunk_id for chunk in self.chunks],
                        use_numpy=self.config.use_vectorized_dense_search,
                    )
                    self._document_model_name = model_name
                    self._dense_index = index
                    if cache is not None:
                        cache.close()
                    return result
                if cache is not None:
                    cache.close()
        raise EmbeddingServiceError("Embedding 后端在构建文档索引期间改变了命名空间")

    def _get_persistent_query_cache(
        self, model_name: str,
    ) -> QueryEmbeddingCache | None:
        if not self.config.query_cache_path:
            return None
        with self._query_cache_lock:
            if time.monotonic() < self._persistent_query_cache_disabled_until:
                return None
            if (
                self._persistent_query_cache is not None
                and self._persistent_query_cache_model == model_name
            ):
                return self._persistent_query_cache
            try:
                cache = QueryEmbeddingCache(
                    self.config.query_cache_path, model_name,
                    ttl_seconds=max(0.0, self.config.query_cache_ttl_seconds),
                    max_entries=max(1, self.config.query_cache_max_entries),
                    busy_timeout_ms=max(100, self.config.cache_busy_timeout_ms),
                    maintenance_interval_seconds=max(
                        0.0, self.config.query_cache_maintenance_interval_seconds,
                    ),
                )
            except (EmbeddingCacheError, OSError, ValueError) as exc:
                self._mark_persistent_query_cache_failure(exc, "初始化")
                return None
            self._persistent_query_cache = cache
            self._persistent_query_cache_model = model_name
            self._persistent_query_cache_error = None
            self._persistent_query_cache_failures = 0
            self._persistent_query_cache_disabled_until = 0.0
            return cache

    def _mark_persistent_query_cache_failure(
        self, exc: Exception, phase: str,
    ) -> None:
        with self._query_cache_lock:
            self._persistent_query_cache = None
            self._persistent_query_cache_model = None
            self._persistent_query_cache_failures += 1
            base = max(0.0, self.config.query_cache_failure_cooldown_seconds)
            delay = min(
                300.0, base * (2 ** max(0, self._persistent_query_cache_failures - 1)),
            ) if base > 0 else 0.0
            self._persistent_query_cache_disabled_until = time.monotonic() + delay
            self._persistent_query_cache_error = (
                f"{phase}持久化查询缓存失败：{_safe_embedding_error(exc)}"
            )

    def _coordinate_persistent_query_misses(
        self, persistent: QueryEmbeddingCache, variants: list[str],
        cached: dict[str, list[float]],
    ) -> tuple[list[str], str, set[str], bool]:
        owner = f"{os.getpid()}:{threading.get_ident()}:{uuid.uuid4().hex}"
        owned: set[str] = set()
        try:
            owned = persistent.try_acquire_leases(
                variants, owner,
                lease_seconds=max(0.001, self.config.query_cache_lease_seconds),
            )
            waiting = set(variants) - owned
            deadline = (
                time.monotonic()
                + max(0.0, self.config.query_cache_cross_process_wait_timeout_seconds)
            )
            while waiting:
                values = persistent.get_many(waiting)
                cached.update(values)
                waiting.difference_update(values)
                if not waiting or time.monotonic() >= deadline:
                    break
                time.sleep(min(0.05, max(0.001, deadline - time.monotonic())))
            if waiting:
                reclaimed = persistent.try_acquire_leases(
                    waiting, owner,
                    lease_seconds=max(0.001, self.config.query_cache_lease_seconds),
                )
                owned.update(reclaimed)
            values = persistent.get_many(variants)
            cached.update(values)
            return [variant for variant in variants if variant not in cached], owner, owned, True
        except (EmbeddingCacheError, OSError, ValueError) as exc:
            if owned:
                try:
                    persistent.release_leases(owned, owner)
                except (EmbeddingCacheError, OSError, ValueError):
                    pass
            self._mark_persistent_query_cache_failure(exc, "跨进程协调")
            return list(variants), "", set(), False

    def _query_vectors(self, variants: list[str]) -> list[list[float]]:
        """Embed variants with TTL/LRU caching and per-key single-flight."""
        size = max(0, self.config.query_cache_size)
        ttl = max(0.0, self.config.query_cache_ttl_seconds)
        wait_timeout = max(0.0, self.config.query_cache_wait_timeout_seconds)
        unique = list(dict.fromkeys(variants))
        if not unique:
            return []

        model_name = _embedding_cache_namespace(self.embedding_backend)
        now = time.monotonic()
        cached: dict[str, list[float]] = {}
        persistent = self._get_persistent_query_cache(model_name)
        persistent_values: dict[str, list[float]] = {}
        if persistent is not None:
            try:
                persistent_values = persistent.get_many(unique)
            except (EmbeddingCacheError, OSError, ValueError) as exc:
                self._mark_persistent_query_cache_failure(exc, "读取")
                persistent = None

        leaders: list[tuple[str, str, _QueryFlight]] = []
        waiters: list[tuple[str, _QueryFlight]] = []
        with self._query_cache_lock:
            for variant in unique:
                key = f"{model_name}\0{variant}"
                item = self._query_cache.get(key) if size else None
                if item is not None and (ttl <= 0 or now - item[0] <= ttl):
                    self._query_cache.move_to_end(key)
                    cached[variant] = item[1]
                    self._query_cache_hits += 1
                    continue
                if item is not None:
                    self._query_cache.pop(key, None)
                durable = persistent_values.get(variant)
                if durable is not None:
                    cached[variant] = durable
                    self._query_cache_hits += 1
                    self._query_cache_persistent_hits += 1
                    if size:
                        self._query_cache[key] = (now, durable)
                        self._query_cache.move_to_end(key)
                    continue
                if persistent is not None:
                    self._query_cache_persistent_misses += 1
                flight = self._query_inflight.get(key)
                if flight is None:
                    flight = _QueryFlight(model_name)
                    self._query_inflight[key] = flight
                    leaders.append((variant, key, flight))
                    self._query_cache_misses += 1
                else:
                    waiters.append((variant, flight))
                    self._query_cache_waits += 1
            while size and len(self._query_cache) > size:
                self._query_cache.popitem(last=False)

        if leaders:
            leader_variants = [item[0] for item in leaders]
            lease_cache = persistent
            lease_owner = ""
            owned_leases: set[str] = set()
            try:
                to_embed = list(leader_variants)
                if persistent is not None:
                    to_embed, lease_owner, owned_leases, persistent_ok = (
                        self._coordinate_persistent_query_misses(
                            persistent, leader_variants, cached,
                        )
                    )
                    if not persistent_ok:
                        persistent = None
                normalized_by_variant: dict[str, list[float]] = {}
                dense_index = self._dense_index
                expected_dimension = (
                    dense_index.dimension if dense_index is not None and dense_index.dimension else None
                )
                for variant in leader_variants:
                    vector = cached.get(variant)
                    if vector is None:
                        continue
                    normalized = validate_embedding_batch(
                        [vector], 1, expected_dimension=expected_dimension,
                        context="查询缓存 Embedding",
                    )[0]
                    expected_dimension = expected_dimension or len(normalized)
                    normalized_by_variant[variant] = normalized
                if to_embed:
                    embedded = self.embedding_backend.embed_queries(to_embed)
                    normalized_batch = validate_embedding_batch(
                        embedded, len(to_embed), expected_dimension=expected_dimension,
                        context="查询 Embedding",
                    )
                    for variant, normalized in zip(to_embed, normalized_batch):
                        normalized_by_variant[variant] = normalized
                if len(normalized_by_variant) != len(leader_variants):
                    raise EmbeddingServiceError("部分查询 Embedding 未获得向量")
                if persistent is not None and to_embed:
                    try:
                        persistent.put_many(
                            (variant, normalized_by_variant[variant]) for variant in to_embed
                        )
                    except (EmbeddingCacheError, OSError, ValueError) as exc:
                        self._mark_persistent_query_cache_failure(exc, "写入")
                with self._query_cache_lock:
                    for variant, key, flight in leaders:
                        normalized = normalized_by_variant[variant]
                        cached[variant] = normalized
                        flight.result = normalized
                        if size:
                            self._query_cache[key] = (time.monotonic(), normalized)
                            self._query_cache.move_to_end(key)
                        if self._query_inflight.get(key) is flight:
                            self._query_inflight.pop(key, None)
                        flight.event.set()
                    while size and len(self._query_cache) > size:
                        self._query_cache.popitem(last=False)
            except Exception as exc:
                with self._query_cache_lock:
                    for _, key, flight in leaders:
                        flight.error = exc
                        if self._query_inflight.get(key) is flight:
                            self._query_inflight.pop(key, None)
                        flight.event.set()
                raise
            finally:
                if lease_cache is not None and owned_leases:
                    try:
                        lease_cache.release_leases(owned_leases, lease_owner)
                    except (EmbeddingCacheError, OSError, ValueError) as exc:
                        self._mark_persistent_query_cache_failure(exc, "释放租约")

        for variant, flight in waiters:
            completed = flight.event.wait(wait_timeout if wait_timeout > 0 else None)
            if not completed:
                raise EmbeddingServiceError("查询 Embedding 等待超时")
            if flight.error is not None:
                raise flight.error
            if flight.result is not None:
                cached[variant] = flight.result
        if not all(variant in cached for variant in unique):
            raise EmbeddingServiceError("部分查询 Embedding 未获得向量")
        return [cached[variant] for variant in variants]

    def _disable_dense(self, exc: Exception, phase: str) -> None:
        message = f"{phase}失败，已回退 BM25：{_safe_embedding_error(exc)}"
        with self._dense_state_lock:
            self.dense_available = False
            self.document_vectors = []
            self._dense_index = None
            self.dense_error = message
            self._dense_state_generation += 1
            cooldown = max(0.0, self.config.dense_recovery_cooldown_seconds)
            self._dense_recovery_next_at = (
                time.monotonic() + cooldown if cooldown > 0 else 0.0
            )

    def _dense_ready(self) -> bool:
        with self._dense_state_lock:
            return bool(self.dense_available)

    def _maybe_recover_dense(self, *, force: bool = False) -> bool:
        if self.config.dense_weight <= 0:
            return False
        with self._dense_state_lock:
            if self.dense_available:
                return True
            cooldown = max(0.0, self.config.dense_recovery_cooldown_seconds)
            if not force and (
                cooldown <= 0 or time.monotonic() < self._dense_recovery_next_at
            ):
                return False
        acquired = self._dense_recovery_lock.acquire(blocking=force)
        if not acquired:
            return False
        try:
            with self._dense_state_lock:
                if self.dense_available:
                    return True
                cooldown = max(0.0, self.config.dense_recovery_cooldown_seconds)
                if not force and (
                    cooldown <= 0 or time.monotonic() < self._dense_recovery_next_at
                ):
                    return False
                generation = self._dense_state_generation
                self._dense_recovery_inflight = True
                self._dense_recovery_attempts += 1
            try:
                self._load_document_vectors()
            except Exception as exc:
                self._disable_dense(exc, "dense 恢复探测")
                return False
            finally:
                with self._dense_state_lock:
                    self._dense_recovery_inflight = False
            with self._dense_state_lock:
                if self._dense_state_generation == generation:
                    self.dense_available = True
                    self.dense_error = None
                    self._dense_recovery_next_at = 0.0
                    self._dense_recovery_successes += 1
                return bool(self.dense_available)
        finally:
            self._dense_recovery_lock.release()

    def recover_dense(self) -> bool:
        return self._maybe_recover_dense(force=True)

    def maintenance(
        self, *, prune_document: bool = False,
        document_valid_ids: Iterable[str] | None = None,
        keep_models: Iterable[str] = (),
        namespace_max_age_seconds: float | None = None,
        namespace_prefix: str | None = None,
        checkpoint_mode: str | None = None, vacuum: bool | None = None,
    ) -> dict[str, Any]:
        with self._maintenance_lock:
            model_name = _embedding_cache_namespace(self.embedding_backend)
            retained = {str(value) for value in keep_models}
            retained.add(model_name)
            max_age = (
                self.config.cache_namespace_max_age_seconds
                if namespace_max_age_seconds is None else namespace_max_age_seconds
            )
            mode = checkpoint_mode or self.config.cache_checkpoint_mode
            vacuum_enabled = (
                self.config.cache_maintenance_vacuum if vacuum is None else bool(vacuum)
            )
            result: dict[str, Any] = {}
            try:
                document_cache = EmbeddingCache(
                    self.config.cache_path, model_name,
                    migrate_legacy=self.config.cache_migrate_legacy,
                    busy_timeout_ms=self.config.cache_busy_timeout_ms,
                )
                result["document_cache"] = document_cache.maintenance(
                    valid_ids=(
                        {str(value) for value in document_valid_ids}
                        if document_valid_ids is not None
                        else {chunk.chunk_id for chunk in self.chunks}
                    ) if prune_document else None,
                    keep_models=retained, namespace_max_age_seconds=max_age,
                    namespace_prefix=namespace_prefix, checkpoint_mode=mode,
                    vacuum=vacuum_enabled,
                )
                document_cache.close()
            except Exception as exc:
                result["document_cache"] = {"error": _safe_embedding_error(exc)}
            persistent = self._get_persistent_query_cache(model_name)
            if persistent is not None:
                try:
                    result["query_cache"] = persistent.maintenance(
                        keep_models=retained, namespace_max_age_seconds=max_age,
                        namespace_prefix=namespace_prefix, checkpoint_mode=mode,
                        vacuum=vacuum_enabled,
                    )
                except Exception as exc:
                    result["query_cache"] = {"error": _safe_embedding_error(exc)}
            else:
                result["query_cache"] = {"enabled": False}
            result["ok"] = not any(
                isinstance(value, dict) and value.get("error") for value in result.values()
            )
            return result

    def status(self) -> dict[str, Any]:
        with self._dense_state_lock:
            dense_index = self._dense_index
            dense_available = self.dense_available
            dense_error = self.dense_error
            next_at = self._dense_recovery_next_at
        with self._query_cache_lock:
            query_entries = len(self._query_cache)
            query_inflight = len(self._query_inflight)
        try:
            cache = EmbeddingCache(
                self.config.cache_path, _embedding_cache_namespace(self.embedding_backend),
                migrate_legacy=self.config.cache_migrate_legacy,
                busy_timeout_ms=self.config.cache_busy_timeout_ms,
            )
            current = {
                chunk.chunk_id: hashlib.sha256(
                    chunk.embedding_text().encode("utf-8")
                ).hexdigest() for chunk in self.chunks
            }
            cache_status = cache.health(current)
            cache.close()
        except Exception as exc:
            cache_status = {"path": str(self.config.cache_path), "error": _safe_embedding_error(exc)}
        health = getattr(self.embedding_backend, "health", None)
        try:
            backend_status = health() if callable(health) else {
                "model": self.embedding_backend.model_name,
            }
        except Exception as exc:
            backend_status = {"error": type(exc).__name__}
        return {
            "chunks": len(self.chunks), "dense_available": dense_available,
            "dense_error": dense_error,
            "dense_index_dimension": dense_index.dimension if dense_index else None,
            "dense_index_memory_bytes": dense_index.memory_bytes if dense_index else 0,
            "document_model": self._document_model_name,
            "cache_namespace": _embedding_cache_namespace(self.embedding_backend),
            "backend": backend_status, "cache": cache_status,
            "query_cache_entries": query_entries,
            "query_cache_limit": self.config.query_cache_size,
            "query_cache_hits": self._query_cache_hits,
            "query_cache_misses": self._query_cache_misses,
            "query_cache_waits": self._query_cache_waits,
            "query_cache_persistent_hits": self._query_cache_persistent_hits,
            "query_cache_persistent_misses": self._query_cache_persistent_misses,
            "query_inflight": query_inflight,
            "dense_recovery_inflight": self._dense_recovery_inflight,
            "dense_recovery_attempts": self._dense_recovery_attempts,
            "dense_recovery_successes": self._dense_recovery_successes,
            "dense_recovery_retry_in_seconds": (
                max(0.0, next_at - time.monotonic()) if next_at > 0 else None
            ),
            "cache_warning": self.cache_warning,
        }

    def _retrieval_mode(self, *, dense_used: bool = False) -> str:
        if dense_used:
            return "hybrid"
        with self._dense_state_lock:
            failed = bool(self.dense_error)
        return "bm25_fallback" if failed else "bm25"

    @staticmethod
    def _context_hit(source: RetrievalHit, chunk: Chunk, relation: str) -> RetrievalHit:
        return RetrievalHit(
            chunk=chunk,
            score=source.score * 0.85,
            lexical_score=0.0,
            dense_score=0.0,
            rerank_score=None,
            context_relation=relation,
            matched_variants=[],
        )

    def expand_context(
        self,
        hits: list[RetrievalHit],
        *,
        neighbors: int = 1,
        primary_limit: int = 3,
    ) -> list[RetrievalHit]:
        """在头部命中之后插入父块内邻接块，再保留其余原始命中。"""
        if neighbors <= 0 or not hits:
            return list(hits)
        primary_count = max(1, min(primary_limit, len(hits)))
        output = list(hits[:primary_count])
        seen = {hit.chunk.chunk_id for hit in hits}
        appended = set()
        for hit in hits[:primary_count]:
            for direction, first_id in (
                ("previous", hit.chunk.previous_chunk_id),
                ("next", hit.chunk.next_chunk_id),
            ):
                chunk_id = first_id
                for _ in range(neighbors):
                    chunk = self._chunks_by_id.get(chunk_id or "")
                    if chunk is None:
                        break
                    if chunk.chunk_id not in seen and chunk.chunk_id not in appended:
                        relation_prefix = (
                            "parent" if chunk.parent_id == hit.chunk.parent_id else "adjacent"
                        )
                        output.append(self._context_hit(
                            hit, chunk, f"{relation_prefix}_{direction}",
                        ))
                        appended.add(chunk.chunk_id)
                    chunk_id = (
                        chunk.previous_chunk_id if direction == "previous"
                        else chunk.next_chunk_id
                    )
        output.extend(hits[primary_count:])
        return output

    @staticmethod
    def _variant_weight(variant: str, original: str, cleaned: str) -> float:
        if variant == original:
            return 2.0
        if variant == cleaned:
            return 1.5
        return 1.0

    @staticmethod
    def _title_key(value: str) -> str:
        text = normalize_query(value, strip_polite=False).casefold()
        text = re.sub(r"\s+", "", text)
        return re.sub(r"(?:实验)?[ab]$", "", text, flags=re.I)

    def _section_adjustment(self, question: str, section: str) -> float:
        normalized = normalize_query(question, strip_polite=True).casefold()
        adjustment = 0.0
        matched_intent = False
        for section_name, terms in self._SECTION_INTENTS.items():
            if section_name in section and any(term in normalized for term in terms):
                adjustment = max(adjustment, self.config.section_intent_boost)
                matched_intent = True
        if (
            not matched_intent
            and any(name in section for name in self._TEMPLATE_SECTIONS)
        ):
            adjustment -= self.config.template_section_penalty
        return adjustment

    def _authority_ranked_indices(
        self,
        question: str,
        ranked: list[int],
        scores: dict[int, float],
        lexical_scores: dict[int, float],
        *,
        dense_used: bool,
    ) -> tuple[list[int], str, bool]:
        """Apply the reviewed source hierarchy before evidence reaches the model."""
        normalized = normalize_query(question, strip_polite=True).casefold()
        example_enabled = any(term in normalized for term in self._EXAMPLE_INTENT_TERMS)
        candidates = [
            index for index in ranked
            if example_enabled or not self.chunks[index].is_example_data
        ]
        primary = [
            index for index in candidates
            if self.chunks[index].source_tier == "primary"
        ]
        primary_sufficient = any(
            (
                scores.get(index, 0.0) >= self.config.primary_minimum_retrieval_score
                if dense_used else
                lexical_scores.get(index, 0.0) >= self.config.primary_minimum_bm25_score
            )
            for index in primary
        )
        if primary_sufficient:
            allowed = {"primary"}
            if example_enabled:
                allowed.add("example")
            return (
                [index for index in candidates if self.chunks[index].source_tier in allowed],
                "primary_only",
                example_enabled,
            )
        secondary_available = any(
            self.chunks[index].source_tier == "secondary" for index in candidates
        )
        return (
            candidates,
            "primary_with_secondary_fallback" if secondary_available else "primary_only",
            example_enabled,
        )

    def _diversify_sources(
        self, hits: list[RetrievalHit], *, top_k: int,
    ) -> list[RetrievalHit]:
        """Prefer source diversity, then fill remaining slots without dropping hits."""
        per_source = self.config.max_hits_per_source_first_pass
        if top_k <= 0 or per_source <= 0:
            return hits[:max(0, top_k)]
        selected: list[RetrievalHit] = []
        overflow: list[RetrievalHit] = []
        counts: dict[str, int] = {}
        for hit in hits:
            source = hit.chunk.source or hit.chunk.experiment_id
            if counts.get(source, 0) < per_source:
                selected.append(hit)
                counts[source] = counts.get(source, 0) + 1
            else:
                overflow.append(hit)
        return (selected + overflow)[:top_k]

    def retrieve(
        self,
        question: str,
        top_k: int = 6,
        *,
        experiment_ids: Iterable[str] | None = None,
    ) -> RetrievalResult:
        started = time.perf_counter()
        original = normalize_query(question, strip_polite=False)
        cleaned = normalize_query(question, strip_polite=True)
        variants = build_query_variants(
            question,
            include_related=should_include_related_expansions(question),
            max_variants=self.config.max_query_variants,
        )
        if not variants or top_k <= 0:
            return RetrievalResult(
                query=question or "", normalized_query=cleaned,
                query_variants=variants, hits=[],
                retrieval_mode=self._retrieval_mode(),
                warnings=[self.dense_error] if self.dense_error else [],
                timings_ms={"total": (time.perf_counter() - started) * 1000},
            )

        if not self._dense_ready():
            self._maybe_recover_dense()
        with self._dense_state_lock:
            dense_ready = bool(self.dense_available)
            current_dense_error = self.dense_error
        scores: dict[int, float] = {}
        lexical_scores: dict[int, float] = {}
        dense_scores: dict[int, float] = {}
        matched: dict[int, list[str]] = {}
        warnings = [current_dense_error] if current_dense_error else []
        if self.cache_warning:
            warnings.append(self.cache_warning)
        rrf_k = self.config.rrf_k

        for variant in variants:
            variant_weight = self._variant_weight(variant, original, cleaned)
            lexical_hits = self.lexical.search(variant, self.config.candidate_k)
            for rank, (index, raw_score) in enumerate(lexical_hits, start=1):
                contribution = self.config.lexical_weight * variant_weight / (rrf_k + rank)
                scores[index] = scores.get(index, 0.0) + contribution
                lexical_scores[index] = max(lexical_scores.get(index, 0.0), raw_score)
                if variant not in matched.setdefault(index, []):
                    matched[index].append(variant)

        dense_used = False
        if dense_ready:
            try:
                if _embedding_cache_namespace(self.embedding_backend) != self._document_model_name:
                    self.document_vectors = self._load_document_vectors()
                query_vectors = self._query_vectors(variants)
                dense_index = self._dense_index
                if dense_index is None:
                    raise EmbeddingServiceError("文档向量索引尚未初始化")
                for variant, query_vector in zip(variants, query_vectors):
                    variant_weight = self._variant_weight(variant, original, cleaned)
                    normalized_query_vector = normalize_vector(query_vector)
                    dense_hits = dense_index.search(
                        normalized_query_vector,
                        threshold=self.config.dense_score_threshold,
                        limit=self.config.candidate_k,
                    )
                    for rank, (index, raw_score) in enumerate(
                        dense_hits[:self.config.candidate_k], start=1,
                    ):
                        contribution = (
                            self.config.dense_weight * variant_weight / (rrf_k + rank)
                        )
                        scores[index] = scores.get(index, 0.0) + contribution
                        dense_scores[index] = max(
                            dense_scores.get(index, -1.0), raw_score
                        )
                        if variant not in matched.setdefault(index, []):
                            matched[index].append(variant)
                dense_used = True
            except Exception as exc:
                if not self.config.allow_bm25_fallback:
                    raise
                self._disable_dense(exc, "查询向量生成")
                with self._dense_state_lock:
                    warning = self.dense_error
                warnings.append(warning or "Embedding 不可用，已回退 BM25")

        query_key = self._title_key(question)
        allowed_experiments = {
            str(experiment_id).strip()
            for experiment_id in (experiment_ids or [])
            if str(experiment_id).strip()
        }
        allowed_experiments |= {
            experiment_id.rsplit("_", 1)[0]
            for experiment_id in tuple(allowed_experiments)
            if re.fullmatch(r"exp\d+_[a-z]", experiment_id, re.I)
        }
        for index in tuple(scores):
            chunk = self.chunks[index]
            title_key = self._title_key(chunk.experiment_name)
            if len(title_key) >= 4 and title_key in query_key:
                scores[index] += self.config.experiment_title_boost
            adjustment = self._section_adjustment(question, chunk.section)
            # 综合复习资料用于补充正式实验指导，不应在内容相近时取代后者。
            if chunk.experiment_id.startswith("reference:"):
                adjustment -= self.config.supplementary_reference_penalty
            scores[index] = max(
                0.0,
                scores[index] + adjustment,
            )
            # 用户上传资料是学生自己的学习上下文，检索融合分上加成，使其优先浮出。
            if chunk.source_kind == "user_upload":
                scores[index] += self.config.user_upload_boost
            if allowed_experiments and chunk.experiment_id in allowed_experiments:
                scores[index] += self.config.page_context_boost

        ranked = sorted(scores, key=lambda index: (-scores[index], self.chunks[index].chunk_id))
        if allowed_experiments and self.config.strict_page_context:
            ranked = [
                index for index in ranked
                if self.chunks[index].experiment_id in allowed_experiments
            ]
        ranked, authority_mode, example_data_enabled = self._authority_ranked_indices(
            question,
            ranked,
            scores,
            lexical_scores,
            dense_used=dense_used,
        )
        if authority_mode == "primary_only" and any(
            self.chunks[index].source_tier == "secondary" for index in scores
        ):
            warnings.append("第一优先级证据达到相关性门槛，未启用第二优先级资料")
        elif authority_mode == "primary_with_secondary_fallback":
            warnings.append("第一优先级证据未达到相关性门槛，已启用第二优先级资料")
        candidate_limit = max(
            top_k,
            self.config.rerank_candidate_k if self.reranker is not None else top_k * 3,
        )
        hits = [RetrievalHit(
            chunk=self.chunks[index], score=scores[index],
            lexical_score=lexical_scores.get(index, 0.0),
            dense_score=dense_scores.get(index, 0.0),
            matched_variants=matched.get(index, []),
        ) for index in ranked[:candidate_limit]]
        rerank_ms = 0.0
        if self.reranker is not None and hits:
            rerank_started = time.perf_counter()
            try:
                hits = self.reranker.rerank(question, hits, top_k=candidate_limit)
            except Exception as exc:
                warnings.append(f"Cross-encoder 重排失败，保留融合排序：{type(exc).__name__}: {exc}")
                hits = hits[:candidate_limit]
            rerank_ms = (time.perf_counter() - rerank_started) * 1000
        else:
            hits = hits[:candidate_limit]
        hits = self._diversify_sources(hits, top_k=top_k)
        return RetrievalResult(
            query=question or "", normalized_query=cleaned,
            query_variants=variants, hits=hits,
            retrieval_mode=self._retrieval_mode(dense_used=dense_used),
            warnings=warnings,
            authority_mode=authority_mode,
            example_data_enabled=example_data_enabled,
            timings_ms={
                "rerank": rerank_ms,
                "total": (time.perf_counter() - started) * 1000,
            },
        )
