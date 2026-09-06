"""Remote/local embedding adapters with validated concurrent requests."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import json
import math
import os
import re
import threading
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from .cache import EmbeddingCache, EmbeddingCacheError


class EmbeddingServiceError(RuntimeError):
    """Normalized embedding failure consumed by the retriever."""

    def __init__(
        self, message: str, *, status_code: int | None = None,
        retryable: bool = False, error_code: str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable
        self.error_code = error_code


class EmbeddingBackend(Protocol):
    model_name: str

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_queries(self, texts: list[str]) -> list[list[float]]: ...


def _env_int(name: str, default: int, *, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise EmbeddingServiceError(f"{name} 必须是整数") from exc
    if value < minimum:
        raise EmbeddingServiceError(f"{name} 必须大于或等于 {minimum}")
    return value


def _env_float(name: str, default: float, *, minimum: float = 0.0) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise EmbeddingServiceError(f"{name} 必须是数字") from exc
    if not math.isfinite(value) or value < minimum:
        raise EmbeddingServiceError(f"{name} 必须大于或等于 {minimum}")
    return value


@dataclass(frozen=True)
class EmbeddingConfig:
    """Generic OpenAI-compatible remote embedding configuration."""

    base_url: str
    api_key: str
    model: str
    batch_size: int = 64
    timeout_seconds: float = 45.0
    max_attempts: int = 2
    retry_base_seconds: float = 0.5
    retry_max_seconds: float = 8.0
    max_concurrency: int = 4
    min_request_interval_seconds: float = 0.0
    dimensions: int | None = None
    cache_revision: str | None = None
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_cooldown_seconds: float = 30.0
    proxy_mode: str = "direct"
    proxy_url: str = ""

    def __post_init__(self) -> None:
        if not str(self.base_url).strip() or not str(self.api_key).strip() or not str(self.model).strip():
            raise EmbeddingServiceError("Embedding 地址、密钥和模型不能为空")
        if self.batch_size <= 0 or self.timeout_seconds <= 0 or self.max_attempts <= 0:
            raise EmbeddingServiceError("Embedding 批大小、超时和尝试次数必须大于 0")
        if self.retry_base_seconds < 0 or self.retry_max_seconds < 0:
            raise EmbeddingServiceError("Embedding 重试等待时间不能为负数")
        if self.max_concurrency <= 0 or self.min_request_interval_seconds < 0:
            raise EmbeddingServiceError("Embedding 并发数和请求间隔配置无效")
        if self.dimensions is not None and self.dimensions <= 0:
            raise EmbeddingServiceError("EMBEDDING_DIMENSIONS 必须大于 0")
        if self.cache_revision is not None and not str(self.cache_revision).strip():
            raise EmbeddingServiceError("EMBEDDING_CACHE_REVISION 不能是空字符串")
        if self.circuit_breaker_failure_threshold < 0:
            raise EmbeddingServiceError("Embedding 熔断失败次数不能为负数")
        if self.circuit_breaker_failure_threshold > 0 and self.circuit_breaker_cooldown_seconds <= 0:
            raise EmbeddingServiceError("启用 Embedding 熔断时冷却时间必须大于 0")
        proxy_mode = str(self.proxy_mode).strip().lower()
        if proxy_mode not in {"direct", "system", "custom"}:
            raise EmbeddingServiceError(
                "EMBEDDING_PROXY_MODE 必须是 direct、system 或 custom"
            )
        if proxy_mode == "custom" and not str(self.proxy_url).strip():
            raise EmbeddingServiceError(
                "EMBEDDING_PROXY_MODE=custom 时必须配置 EMBEDDING_PROXY_URL"
            )
        object.__setattr__(self, "proxy_mode", proxy_mode)
        object.__setattr__(self, "proxy_url", str(self.proxy_url).strip())

    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        base_url = os.getenv("EMBEDDING_BASE_URL") or os.getenv("LLM_BASE_URL", "")
        api_key = os.getenv("EMBEDDING_API_KEY") or os.getenv("LLM_API_KEY", "")
        model = os.getenv("EMBEDDING_MODEL", "")
        missing = [name for name, value in (
            ("EMBEDDING_BASE_URL/LLM_BASE_URL", base_url),
            ("EMBEDDING_API_KEY/LLM_API_KEY", api_key),
            ("EMBEDDING_MODEL", model),
        ) if not value]
        if missing:
            raise EmbeddingServiceError("缺少 Embedding 配置: " + ", ".join(missing))
        dimensions_raw = os.getenv("EMBEDDING_DIMENSIONS", "").strip()
        dimensions = _env_int("EMBEDDING_DIMENSIONS", 1) if dimensions_raw else None
        return cls(
            base_url=base_url, api_key=api_key, model=model,
            batch_size=_env_int("EMBEDDING_BATCH_SIZE", 64),
            timeout_seconds=_env_float("EMBEDDING_TIMEOUT_SECONDS", 45.0, minimum=0.1),
            max_attempts=_env_int("EMBEDDING_MAX_ATTEMPTS", 2),
            retry_base_seconds=_env_float("EMBEDDING_RETRY_BASE_SECONDS", 0.5),
            retry_max_seconds=_env_float("EMBEDDING_RETRY_MAX_SECONDS", 8.0),
            max_concurrency=_env_int("EMBEDDING_MAX_CONCURRENCY", 4),
            min_request_interval_seconds=_env_float(
                "EMBEDDING_MIN_REQUEST_INTERVAL_SECONDS", 0.0,
            ),
            dimensions=dimensions,
            cache_revision=os.getenv("EMBEDDING_CACHE_REVISION", "").strip() or None,
            circuit_breaker_failure_threshold=_env_int(
                "EMBEDDING_CIRCUIT_BREAKER_FAILURES", 3, minimum=0,
            ),
            circuit_breaker_cooldown_seconds=_env_float(
                "EMBEDDING_CIRCUIT_BREAKER_COOLDOWN_SECONDS", 30.0,
            ),
            proxy_mode=os.getenv(
                "EMBEDDING_PROXY_MODE", os.getenv("CHAT_PROXY_MODE", "direct"),
            ),
            proxy_url=os.getenv(
                "EMBEDDING_PROXY_URL", os.getenv("CHAT_PROXY_URL", ""),
            ),
        )


@dataclass(frozen=True)
class LocalEmbeddingConfig:
    """Configuration for an explicitly local SentenceTransformer model."""

    model: str
    device: str = "cpu"
    batch_size: int = 32
    local_files_only: bool = True

    @classmethod
    def from_env(cls) -> "LocalEmbeddingConfig":
        model = os.getenv("LOCAL_EMBEDDING_MODEL", "").strip()
        if not model:
            raise EmbeddingServiceError("缺少本地 Embedding 配置: LOCAL_EMBEDDING_MODEL")
        try:
            batch_size = max(1, int(os.getenv("LOCAL_EMBEDDING_BATCH_SIZE", "32")))
        except ValueError as exc:
            raise EmbeddingServiceError("LOCAL_EMBEDDING_BATCH_SIZE 必须是整数") from exc
        allow_download = os.getenv("LOCAL_EMBEDDING_ALLOW_DOWNLOAD", "0").strip().lower()
        return cls(
            model=model,
            device=os.getenv("LOCAL_EMBEDDING_DEVICE", "cpu").strip() or "cpu",
            batch_size=batch_size,
            local_files_only=allow_download not in {"1", "true", "yes", "on"},
        )


def normalize_vector(vector: list[float]) -> list[float]:
    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError, OverflowError) as exc:
        raise EmbeddingServiceError("Embedding 服务返回了非数字向量") from exc
    if not values or any(not math.isfinite(value) for value in values):
        raise EmbeddingServiceError("Embedding 服务返回了空向量或非有限数值")
    try:
        norm = math.hypot(*values)
    except (OverflowError, ValueError) as exc:
        raise EmbeddingServiceError("Embedding 服务返回了无效向量范数") from exc
    if not math.isfinite(norm) or norm <= 0:
        raise EmbeddingServiceError("Embedding 服务返回了零向量或无效向量范数")
    return [value / norm for value in values]


def validate_embedding_batch(
    vectors: object, expected_count: int, *, expected_dimension: int | None = None,
    context: str = "Embedding",
) -> list[list[float]]:
    """Normalize and validate count, dimensions and numeric values."""
    try:
        rows = vectors.tolist() if hasattr(vectors, "tolist") else list(vectors)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise EmbeddingServiceError(f"{context} 返回结果不可迭代") from exc
    if expected_count == 1 and rows and not isinstance(rows[0], (list, tuple)):
        rows = [rows]
    if len(rows) != expected_count:
        raise EmbeddingServiceError(
            f"{context} 返回向量数量不正确（期望 {expected_count}，实际 {len(rows)}）"
        )
    result: list[list[float]] = []
    dimension = expected_dimension
    for row in rows:
        try:
            values = row.tolist() if hasattr(row, "tolist") else list(row)
            vector = normalize_vector(values)
        except (TypeError, ValueError, EmbeddingServiceError) as exc:
            raise EmbeddingServiceError(f"{context} 返回了无效向量") from exc
        if dimension is None:
            dimension = len(vector)
        elif len(vector) != dimension:
            raise EmbeddingServiceError(f"{context} 向量维度不一致")
        result.append(vector)
    return result


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise EmbeddingServiceError("查询向量与文档向量维度不一致")
    return sum(a * b for a, b in zip(left, right))


_REDACTED_SECRET_RE = re.compile(r"(?:sk|api|key)[-_][A-Za-z0-9._~-]{8,}", re.I)


def _redact_message(value: object) -> str:
    return _REDACTED_SECRET_RE.sub("[REDACTED]", str(value or ""))[:500]


class RemoteEmbeddingBackend:
    """Generic OpenAI-compatible client with bounded retries and concurrency."""

    _RETRYABLE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}

    def __init__(self, config: EmbeddingConfig, *, opener=None):
        self.config = config
        self.model_name = config.model
        self._opener = opener or self._build_opener(config)
        self._semaphore = threading.BoundedSemaphore(config.max_concurrency)
        self._rate_lock = threading.Lock()
        self._next_request_at = 0.0
        self._stats_lock = threading.Lock()
        self._dimension_lock = threading.Lock()
        self._dimension = config.dimensions
        self._executor_lock = threading.Lock()
        self._executor: ThreadPoolExecutor | None = None
        self._circuit_open_until = 0.0
        self._circuit_probe_inflight = False
        self._stats: dict[str, Any] = {
            "requests": 0, "retries": 0, "failures": 0,
            "consecutive_failures": 0, "circuit_trips": 0,
            "positional_index_fallbacks": 0,
            "last_status": None, "last_error": None,
        }

    @staticmethod
    def _build_opener(config: EmbeddingConfig):
        if config.proxy_mode == "direct":
            return build_opener(ProxyHandler({}))
        if config.proxy_mode == "custom":
            proxies = {"http": config.proxy_url, "https": config.proxy_url}
            return build_opener(ProxyHandler(proxies))
        return build_opener(ProxyHandler())

    @property
    def cache_namespace(self) -> str:
        identity = "|".join((
            self.config.base_url.rstrip("/"), self.model_name,
            str(self.config.dimensions or "auto"),
            str(self.config.cache_revision or ""),
        ))
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]
        return f"{self.model_name}:remote-{digest}"

    @property
    def dimension(self) -> int | None:
        with self._dimension_lock:
            return self._dimension

    def _endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return base if base.endswith("/embeddings") else base + "/embeddings"

    def _ensure_circuit_available(self) -> None:
        now = time.monotonic()
        with self._stats_lock:
            if self._circuit_open_until > now:
                raise EmbeddingServiceError(
                    "Embedding 服务暂时熔断", retryable=True, error_code="circuit_open",
                )
            if self._circuit_open_until > 0:
                if self._circuit_probe_inflight:
                    raise EmbeddingServiceError(
                        "Embedding 服务正在恢复探测", retryable=True,
                        error_code="circuit_probe_inflight",
                    )
                self._circuit_probe_inflight = True

    def _record_success(self) -> None:
        with self._stats_lock:
            self._stats["consecutive_failures"] = 0
            self._stats["last_error"] = None
            self._circuit_open_until = 0.0
            self._circuit_probe_inflight = False

    def _record_failure(self, error: EmbeddingServiceError) -> None:
        with self._stats_lock:
            self._stats["failures"] += 1
            self._stats["last_error"] = _redact_message(error)
            self._circuit_probe_inflight = False
            if not error.retryable:
                self._stats["consecutive_failures"] = 0
                self._circuit_open_until = 0.0
                return
            self._stats["consecutive_failures"] += 1
            threshold = self.config.circuit_breaker_failure_threshold
            if threshold and self._stats["consecutive_failures"] >= threshold:
                self._circuit_open_until = (
                    time.monotonic() + self.config.circuit_breaker_cooldown_seconds
                )
                self._stats["circuit_trips"] += 1

    def _wait_for_rate_slot(self) -> None:
        interval = self.config.min_request_interval_seconds
        if interval <= 0:
            return
        with self._rate_lock:
            now = time.monotonic()
            wait = max(0.0, self._next_request_at - now)
            self._next_request_at = max(now, self._next_request_at) + interval
        if wait:
            time.sleep(wait)

    @staticmethod
    def _retry_after(exc: HTTPError) -> float | None:
        try:
            value = exc.headers.get("Retry-After") if exc.headers else None
            return None if value is None else max(0.0, min(float(value), 60.0))
        except (AttributeError, TypeError, ValueError):
            return None

    @classmethod
    def _http_error(cls, exc: HTTPError) -> EmbeddingServiceError:
        detail = ""
        error_code = None
        try:
            body = json.loads(exc.read(4096).decode("utf-8", errors="replace"))
            error = body.get("error", {}) if isinstance(body, dict) else {}
            if isinstance(error, dict):
                detail = _redact_message(str(error.get("message", "")).strip())
                code = error.get("code")
                error_code = str(code)[:100] if code is not None else None
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError):
            pass
        message = f"Embedding HTTP {exc.code}" + (f": {detail}" if detail else "")
        return EmbeddingServiceError(
            message, status_code=exc.code,
            retryable=exc.code in cls._RETRYABLE_STATUS_CODES,
            error_code=error_code,
        )

    def _parse_response(self, body: object, expected: int) -> list[list[float]]:
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            raise EmbeddingServiceError("Embedding 响应不是有效的 JSON 数据对象")
        rows = body["data"]
        if len(rows) != expected:
            raise EmbeddingServiceError("Embedding 响应数量不正确")
        try:
            indices = [int(row["index"]) for row in rows]
            vectors = [row["embedding"] for row in rows]
        except (TypeError, ValueError, KeyError) as exc:
            raise EmbeddingServiceError("Embedding 响应 index 或向量无效") from exc
        expected_indices = list(range(expected))
        if sorted(indices) == expected_indices:
            vectors = [
                vector for _, vector in sorted(zip(indices, vectors), key=lambda item: item[0])
            ]
        elif expected > 1 and len(set(indices)) == 1:
            # DashScope 的部分兼容模型会为批量响应中的每一项都返回 index=0，
            # 但响应顺序仍与输入顺序一致。仅针对“全部索引相同”这一确定格式
            # 使用位置顺序；其他缺失、越界或部分重复仍视为无效响应。
            with self._stats_lock:
                self._stats["positional_index_fallbacks"] += 1
        else:
            raise EmbeddingServiceError("Embedding 响应 index 缺失或重复")
        with self._dimension_lock:
            expected_dimension = self._dimension
        normalized = validate_embedding_batch(
            vectors, expected, expected_dimension=expected_dimension,
            context="Remote Embedding",
        )
        if normalized:
            with self._dimension_lock:
                if self._dimension is None:
                    self._dimension = len(normalized[0])
                elif len(normalized[0]) != self._dimension:
                    raise EmbeddingServiceError("Remote Embedding 向量维度发生变化")
        return normalized

    def _request_batch(self, batch: list[str]) -> list[list[float]]:
        self._ensure_circuit_available()
        payload_data: dict[str, Any] = {"model": self.config.model, "input": batch}
        if self.config.dimensions is not None:
            payload_data["dimensions"] = self.config.dimensions
        payload = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
        last_error: EmbeddingServiceError | None = None
        for attempt in range(self.config.max_attempts):
            request = Request(self._endpoint(), data=payload, method="POST", headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json", "Accept": "application/json",
            })
            retry_after = None
            with self._stats_lock:
                self._stats["requests"] += 1
            try:
                self._wait_for_rate_slot()
                with self._semaphore:
                    with self._opener.open(
                        request, timeout=self.config.timeout_seconds,
                    ) as response:
                        body = json.load(response)
                vectors = self._parse_response(body, len(batch))
                with self._stats_lock:
                    self._stats["last_status"] = 200
                self._record_success()
                return vectors
            except HTTPError as exc:
                last_error = self._http_error(exc)
                retry_after = self._retry_after(exc)
                with self._stats_lock:
                    self._stats["last_status"] = exc.code
            except EmbeddingServiceError as exc:
                last_error = exc
            except (
                URLError, TimeoutError, OSError, UnicodeError, json.JSONDecodeError,
            ) as exc:
                last_error = EmbeddingServiceError(
                    f"Embedding 网络或响应失败: {_redact_message(exc)}", retryable=True,
                )
            if not last_error.retryable or attempt + 1 >= self.config.max_attempts:
                break
            with self._stats_lock:
                self._stats["retries"] += 1
            delay = retry_after
            if delay is None:
                delay = min(
                    self.config.retry_max_seconds,
                    self.config.retry_base_seconds * (2 ** attempt),
                )
            if delay:
                time.sleep(delay)
        error = last_error or EmbeddingServiceError("Embedding 请求失败")
        self._record_failure(error)
        raise error

    def _executor_for_batches(self) -> ThreadPoolExecutor:
        with self._executor_lock:
            if self._executor is None:
                self._executor = ThreadPoolExecutor(
                    max_workers=self.config.max_concurrency,
                    thread_name_prefix="remote-embedding",
                )
            return self._executor

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        batches = [
            texts[start:start + self.config.batch_size]
            for start in range(0, len(texts), self.config.batch_size)
        ]
        with self._stats_lock:
            recovering = self._circuit_open_until > 0
        results: list[list[list[float]]] = []
        if recovering:
            results.append(self._request_batch(batches[0]))
            batches = batches[1:]
        if len(batches) <= 1 or self.config.max_concurrency == 1:
            results.extend(self._request_batch(batch) for batch in batches)
        else:
            futures = [
                self._executor_for_batches().submit(self._request_batch, batch)
                for batch in batches
            ]
            results.extend(future.result() for future in futures)
        vectors = [vector for batch in results for vector in batch]
        if len(vectors) != len(texts):
            raise EmbeddingServiceError("Embedding 返回数量与输入不一致")
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def health(self) -> dict[str, Any]:
        with self._stats_lock:
            stats = dict(self._stats)
            remaining = max(0.0, self._circuit_open_until - time.monotonic())
            probe = self._circuit_probe_inflight
        return {
            "backend": "remote", "model": self.model_name,
            "cache_namespace": self.cache_namespace, "dimensions": self.dimension,
            "batch_size": self.config.batch_size,
            "max_concurrency": self.config.max_concurrency,
            "proxy_mode": self.config.proxy_mode,
            "circuit_open": remaining > 0,
            "circuit_remaining_seconds": round(remaining, 3),
            "circuit_probe_inflight": probe, **stats,
        }

    def close(self) -> None:
        with self._executor_lock:
            executor = self._executor
            self._executor = None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=False)


class LocalSentenceTransformerBackend:
    """Lazy local embedding backend; it never downloads unless explicitly allowed."""

    def __init__(self, config: LocalEmbeddingConfig, *, model: Any | None = None):
        self.config = config
        self.model_name = f"local-sentence-transformers:{config.model}"
        self.cache_namespace = self.model_name
        self._model = model
        self._model_lock = threading.Lock()

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is not None:
                return self._model
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingServiceError(
                    "本地 Embedding 需要安装 sentence-transformers"
                ) from exc
            try:
                self._model = SentenceTransformer(
                    self.config.model, device=self.config.device,
                    local_files_only=self.config.local_files_only,
                )
            except Exception as exc:
                mode = "离线" if self.config.local_files_only else "允许下载"
                raise EmbeddingServiceError(
                    f"本地 Embedding 模型加载失败（{mode}）: {type(exc).__name__}: {exc}"
                ) from exc
            return self._model

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            encoded = self._get_model().encode(
                texts, batch_size=self.config.batch_size,
                normalize_embeddings=True, show_progress_bar=False,
            )
            return validate_embedding_batch(
                encoded, len(texts), context="Local Embedding",
            )
        except EmbeddingServiceError:
            raise
        except Exception as exc:
            raise EmbeddingServiceError(
                f"本地 Embedding 编码失败: {type(exc).__name__}: {exc}"
            ) from exc

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def health(self) -> dict[str, Any]:
        return {
            "backend": "local", "model": self.model_name,
            "cache_namespace": self.cache_namespace, "loaded": self._model is not None,
        }

    def close(self) -> None:
        return None


class BM25OnlyEmbeddingBackend:
    """Placeholder backend used when dense retrieval is explicitly disabled."""

    model_name = "bm25-only"
    cache_namespace = model_name

    @staticmethod
    def _disabled() -> list[list[float]]:
        raise EmbeddingServiceError("当前配置为仅使用 BM25")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._disabled()

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self._disabled()

    def health(self) -> dict[str, Any]:
        return {"backend": "bm25", "model": self.model_name}

    def close(self) -> None:
        return None


__all__ = [
    "BM25OnlyEmbeddingBackend", "EmbeddingBackend", "EmbeddingCache",
    "EmbeddingCacheError", "EmbeddingConfig", "EmbeddingServiceError",
    "LocalEmbeddingConfig", "LocalSentenceTransformerBackend",
    "RemoteEmbeddingBackend", "cosine_similarity", "normalize_vector",
    "validate_embedding_batch",
]
