"""Concurrent persistent caches for document and query embeddings."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import struct
import threading
import time
from typing import Iterable, Mapping


class EmbeddingCacheError(OSError):
    """Raised when cache storage is unavailable or contains invalid vectors."""


def _valid_vector(vector: object) -> list[float] | None:
    if not isinstance(vector, (list, tuple)) or not vector:
        return None
    try:
        values = [float(value) for value in vector]
    except (TypeError, ValueError, OverflowError):
        return None
    return values if all(math.isfinite(value) for value in values) else None


def _current_key_map(
    current: set[str] | Mapping[str, str] | None,
) -> dict[str, str | None]:
    if not current:
        return {}
    if isinstance(current, Mapping):
        return {str(key): str(value) for key, value in current.items()}
    return {str(value): None for value in current}


@contextmanager
def _exclusive_file_lock(path: Path, timeout_seconds: float = 15.0):
    """Lock one byte in a sidecar file on Windows and POSIX."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    locked = False
    try:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    locked = True
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise EmbeddingCacheError(f"缓存锁等待超时: {path}") from exc
                    time.sleep(0.05)
        else:
            import fcntl

            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                    break
                except BlockingIOError as exc:
                    if time.monotonic() >= deadline:
                        raise EmbeddingCacheError(f"缓存锁等待超时: {path}") from exc
                    time.sleep(0.05)
        yield
    finally:
        if locked:
            try:
                if os.name == "nt":
                    import msvcrt

                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


class _JsonEmbeddingCache:
    """Compatibility backend for callers that explicitly keep a .json path."""

    version = 3

    def __init__(self, path: Path, model_name: str):
        self.path = path
        self.model_name = model_name
        self.entries: dict[str, dict] = {}
        self._dirty: dict[str, dict] = {}
        self._deleted: set[str] = set()
        self._clear_requested = False
        self._loaded_generation = 0
        self._lock = threading.RLock()
        self._load()

    @staticmethod
    def _read(path: Path, model_name: str) -> tuple[dict[str, dict], int]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}, 0
        if not isinstance(payload, dict) or payload.get("model") != model_name:
            return {}, 0
        try:
            generation = max(0, int(payload.get("clear_generation", 0) or 0))
        except (TypeError, ValueError):
            generation = 0
        entries = {}
        for key, item in (payload.get("entries") or {}).items():
            vector = _valid_vector(item.get("vector")) if isinstance(item, dict) else None
            if vector is not None and isinstance(item.get("text_hash"), str):
                entries[str(key)] = {"text_hash": item["text_hash"], "vector": vector}
        return entries, generation

    def _load(self) -> None:
        self.entries, self._loaded_generation = self._read(self.path, self.model_name)

    def get(self, chunk_id: str, text_hash: str) -> list[float] | None:
        with self._lock:
            item = self.entries.get(str(chunk_id))
            if not item or item.get("text_hash") != str(text_hash):
                return None
            return _valid_vector(item.get("vector"))

    def get_many(self, keys: Iterable[tuple[str, str]]) -> dict[str, list[float]]:
        requested = {str(chunk_id): str(text_hash) for chunk_id, text_hash in keys}
        with self._lock:
            result = {}
            by_hash: dict[str, list[float]] = {}
            for item in self.entries.values():
                vector = _valid_vector(item.get("vector"))
                text_hash = item.get("text_hash")
                if vector is not None and isinstance(text_hash, str):
                    by_hash.setdefault(text_hash, vector)
            for chunk_id, text_hash in requested.items():
                item = self.entries.get(chunk_id)
                vector = _valid_vector(item.get("vector")) if item else None
                if item and item.get("text_hash") == text_hash and vector is not None:
                    result[chunk_id] = vector
                elif text_hash in by_hash:
                    result[chunk_id] = list(by_hash[text_hash])
            return result

    def put(self, chunk_id: str, text_hash: str, vector: list[float]) -> None:
        values = _valid_vector(vector)
        if values is None:
            raise EmbeddingCacheError("不能缓存空向量或非有限向量")
        with self._lock:
            key = str(chunk_id)
            entry = {"text_hash": str(text_hash), "vector": values}
            self.entries[key] = entry
            self._dirty[key] = entry
            self._deleted.discard(key)

    def put_many(self, values: Iterable[tuple[str, str, list[float]]]) -> None:
        for chunk_id, text_hash, vector in values:
            self.put(chunk_id, text_hash, vector)

    def save(self) -> None:
        lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        with self._lock, _exclusive_file_lock(lock_path):
            latest, generation = self._read(self.path, self.model_name)
            if self._clear_requested:
                latest = {}
                generation = max(generation, self._loaded_generation) + 1
            elif generation > self._loaded_generation:
                self.entries = {}
                self._dirty.clear()
                self._deleted.clear()
                self._loaded_generation = generation
                return
            else:
                latest.update(self._dirty)
                for key in self._deleted:
                    latest.pop(key, None)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_name(
                f".{self.path.name}.{os.getpid()}.{threading.get_ident()}.tmp"
            )
            try:
                with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                    json.dump({
                        "version": self.version,
                        "model": self.model_name,
                        "clear_generation": generation,
                        "entries": latest,
                    }, handle, ensure_ascii=False, allow_nan=False)
                    handle.write("\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, self.path)
            except OSError as exc:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                raise EmbeddingCacheError(f"写入 Embedding JSON 缓存失败: {exc}") from exc
            self.entries = latest
            self._dirty.clear()
            self._deleted.clear()
            self._clear_requested = False
            self._loaded_generation = generation

    def snapshot(self, current_ids: set[str] | Mapping[str, str] | None = None) -> dict:
        current = _current_key_map(current_ids)
        with self._lock:
            dimension = None
            if self.entries:
                vector = _valid_vector(next(iter(self.entries.values())).get("vector"))
                dimension = len(vector) if vector else None
            current_count = sum(
                1 for key, text_hash in current.items()
                if key in self.entries
                and (text_hash is None or self.entries[key].get("text_hash") == text_hash)
            ) if current else len(self.entries)
            count = len(self.entries)
        return {
            "format": "json", "path": str(self.path), "model": self.model_name,
            "exists": self.path.is_file(),
            "bytes": self.path.stat().st_size if self.path.is_file() else 0,
            "entries": count, "dimension": dimension,
            "current_entries": current_count,
            "missing_current_entries": max(0, len(current) - current_count),
            "stale_entries": max(0, count - current_count) if current else 0,
        }

    def prune(self, valid_ids: set[str]) -> int:
        with self._lock:
            stale = set(self.entries) - {str(value) for value in valid_ids}
            for key in stale:
                self.entries.pop(key, None)
                self._dirty.pop(key, None)
                self._deleted.add(key)
        if stale:
            self.save()
        return len(stale)

    def clear_model(self) -> int:
        with self._lock:
            count = len(self.entries)
            self.entries.clear()
            self._dirty.clear()
            self._deleted.clear()
            self._clear_requested = True
        self.save()
        return count

    def list_namespaces(self) -> list[dict]:
        snapshot = self.snapshot()
        return [{
            "model": self.model_name, "entries": snapshot["entries"],
            "dimension": snapshot["dimension"], "cleared": snapshot["entries"] == 0,
            "last_updated": self.path.stat().st_mtime if self.path.is_file() else None,
        }]

    def clear_namespaces(self, names: Iterable[str]) -> int:
        values = {names.strip()} if isinstance(names, str) else {
            str(name).strip() for name in names if str(name).strip()
        }
        return self.clear_model() if self.model_name in values else 0

    def checkpoint(self, mode: str = "PASSIVE") -> dict:
        return {"backend": "json", "mode": str(mode).upper(), "skipped": True}

    def maintenance(
        self, *, valid_ids: set[str] | None = None,
        keep_models: Iterable[str] = (), namespace_max_age_seconds: float | None = None,
        namespace_prefix: str | None = None, checkpoint_mode: str = "PASSIVE",
        vacuum: bool = False,
    ) -> dict:
        del keep_models, namespace_max_age_seconds, namespace_prefix, vacuum
        pruned = self.prune(valid_ids) if valid_ids is not None else 0
        return {
            "backend": "json", "pruned_entries": pruned,
            "removed_namespace_entries": 0,
            "checkpoint": self.checkpoint(checkpoint_mode), "vacuum": False,
            "snapshot": self.snapshot(),
        }

    def health(self, current_ids: set[str] | Mapping[str, str] | None = None) -> dict:
        result = self.snapshot(current_ids)
        result.update({"backend": "json-document", "namespace_count": 1})
        return result

    def close(self) -> None:
        return None


class _SQLiteBase:
    _IN_BATCH_SIZE = 800

    def __init__(self, path: Path, *, busy_timeout_ms: int):
        self.path = path
        self.busy_timeout_ms = max(100, int(busy_timeout_ms))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            str(self.path), timeout=self.busy_timeout_ms / 1000.0,
            isolation_level=None,
        )
        connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def _run(self, operation, *, write: bool = False):
        connection: sqlite3.Connection | None = None
        try:
            connection = self._connect()
            if write:
                connection.execute("BEGIN IMMEDIATE")
            result = operation(connection)
            if write:
                connection.commit()
            return result
        except (sqlite3.Error, OSError, ValueError) as exc:
            if connection is not None and write:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
            raise EmbeddingCacheError(f"SQLite Embedding 缓存失败: {exc}") from exc
        finally:
            if connection is not None:
                connection.close()

    @staticmethod
    def _pack(vector: list[float]) -> bytes:
        values = _valid_vector(vector)
        if values is None:
            raise EmbeddingCacheError("不能缓存空向量或非有限向量")
        return struct.pack(f"<{len(values)}f", *values)

    @staticmethod
    def _unpack(blob: object, dimension: int) -> list[float] | None:
        if not isinstance(blob, (bytes, bytearray, memoryview)) or dimension <= 0:
            return None
        raw = bytes(blob)
        if len(raw) != dimension * 4:
            return None
        values = list(struct.unpack(f"<{dimension}f", raw))
        return values if all(math.isfinite(value) for value in values) else None

    @staticmethod
    def _checkpoint_mode(mode: str) -> str:
        value = str(mode).upper()
        if value not in {"PASSIVE", "FULL", "RESTART", "TRUNCATE"}:
            raise EmbeddingCacheError("SQLite checkpoint 模式无效")
        return value

    def checkpoint(self, mode: str = "PASSIVE") -> dict:
        value = self._checkpoint_mode(mode)
        row = self._run(lambda connection: connection.execute(
            f"PRAGMA wal_checkpoint({value})"
        ).fetchone())
        return {
            "backend": "sqlite", "mode": value,
            "busy": int(row[0]) if row else 0,
            "log_frames": int(row[1]) if row else 0,
            "checkpointed_frames": int(row[2]) if row else 0,
        }

    def close(self) -> None:
        return None


class _SQLiteEmbeddingCache(_SQLiteBase):
    version = 3

    def __init__(
        self, path: Path, model_name: str, *, busy_timeout_ms: int = 15000,
        migrate_json: bool = True,
    ):
        super().__init__(path, busy_timeout_ms=busy_timeout_ms)
        self.model_name = str(model_name)
        self._initialize()
        if migrate_json:
            self._migrate_legacy_json()

    def _initialize(self) -> None:
        def initialize(connection: sqlite3.Connection):
            connection.execute("""CREATE TABLE IF NOT EXISTS rag_embedding_cache_meta (
                model_name TEXT PRIMARY KEY,
                dimension INTEGER,
                backend TEXT NOT NULL DEFAULT 'sqlite',
                updated_at REAL NOT NULL DEFAULT 0,
                cleared INTEGER NOT NULL DEFAULT 0
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS rag_embedding_cache (
                model_name TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                vector BLOB NOT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL DEFAULT 0,
                PRIMARY KEY (model_name, chunk_id)
            )""")
            for table, column, definition in (
                ("rag_embedding_cache_meta", "backend", "TEXT NOT NULL DEFAULT 'sqlite'"),
                ("rag_embedding_cache_meta", "updated_at", "REAL NOT NULL DEFAULT 0"),
                ("rag_embedding_cache_meta", "cleared", "INTEGER NOT NULL DEFAULT 0"),
                ("rag_embedding_cache", "updated_at", "REAL NOT NULL DEFAULT 0"),
            ):
                columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
                if column not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            connection.execute("""CREATE INDEX IF NOT EXISTS rag_embedding_cache_hash_idx
                ON rag_embedding_cache(model_name, text_hash)""")
            connection.execute("""CREATE INDEX IF NOT EXISTS rag_embedding_cache_updated_idx
                ON rag_embedding_cache(model_name, updated_at)""")
        self._run(initialize, write=True)

    def _dimension(self, connection: sqlite3.Connection) -> int | None:
        row = connection.execute(
            "SELECT dimension FROM rag_embedding_cache_meta WHERE model_name=?",
            (self.model_name,),
        ).fetchone()
        return int(row[0]) if row and row[0] else None

    def get(self, chunk_id: str, text_hash: str) -> list[float] | None:
        return self.get_many([(chunk_id, text_hash)]).get(str(chunk_id))

    def get_many(self, keys: Iterable[tuple[str, str]]) -> dict[str, list[float]]:
        requested = {str(chunk_id): str(text_hash) for chunk_id, text_hash in keys}
        if not requested:
            return {}

        def read(connection: sqlite3.Connection):
            result: dict[str, list[float]] = {}
            items = list(requested.items())
            for start in range(0, len(items), self._IN_BATCH_SIZE):
                batch = items[start:start + self._IN_BATCH_SIZE]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"SELECT chunk_id,text_hash,dimension,vector FROM rag_embedding_cache "
                    f"WHERE model_name=? AND chunk_id IN ({placeholders})",
                    (self.model_name, *(item[0] for item in batch)),
                )
                for chunk_id, text_hash, dimension, blob in rows:
                    if requested.get(chunk_id) == text_hash:
                        vector = self._unpack(blob, int(dimension))
                        if vector is not None:
                            result[chunk_id] = vector
            missing_hashes = {
                text_hash for chunk_id, text_hash in requested.items() if chunk_id not in result
            }
            by_hash: dict[str, list[float]] = {}
            values = list(missing_hashes)
            for start in range(0, len(values), self._IN_BATCH_SIZE):
                batch = values[start:start + self._IN_BATCH_SIZE]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"SELECT text_hash,dimension,vector FROM rag_embedding_cache "
                    f"WHERE model_name=? AND text_hash IN ({placeholders})",
                    (self.model_name, *batch),
                )
                for text_hash, dimension, blob in rows:
                    vector = self._unpack(blob, int(dimension))
                    if vector is not None:
                        by_hash.setdefault(text_hash, vector)
            for chunk_id, text_hash in requested.items():
                if chunk_id not in result and text_hash in by_hash:
                    result[chunk_id] = list(by_hash[text_hash])
            return result
        return self._run(read)

    def put(self, chunk_id: str, text_hash: str, vector: list[float]) -> None:
        self.put_many([(chunk_id, text_hash, vector)])

    def put_many(self, values: Iterable[tuple[str, str, list[float]]]) -> None:
        prepared = []
        batch_dimension = None
        for chunk_id, text_hash, vector in values:
            checked = _valid_vector(vector)
            if checked is None:
                raise EmbeddingCacheError("不能缓存空向量或非有限向量")
            batch_dimension = batch_dimension or len(checked)
            if len(checked) != batch_dimension:
                raise EmbeddingCacheError("同一缓存批次的向量维度不一致")
            prepared.append((str(chunk_id), str(text_hash), checked))
        if not prepared:
            return

        def write(connection: sqlite3.Connection):
            current = self._dimension(connection)
            if current is not None and current != batch_dimension:
                raise ValueError(
                    f"缓存向量维度不一致（已有 {current}，新值 {batch_dimension}）"
                )
            now = time.time()
            connection.execute("""INSERT INTO rag_embedding_cache_meta(
                model_name,dimension,backend,updated_at,cleared
            ) VALUES(?,?,?,?,0) ON CONFLICT(model_name) DO UPDATE SET
                dimension=excluded.dimension,backend='sqlite',updated_at=excluded.updated_at,
                cleared=0""", (self.model_name, batch_dimension, "sqlite", now))
            connection.executemany("""INSERT INTO rag_embedding_cache(
                model_name,chunk_id,text_hash,dimension,vector,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?) ON CONFLICT(model_name,chunk_id) DO UPDATE SET
                text_hash=excluded.text_hash,dimension=excluded.dimension,
                vector=excluded.vector,updated_at=excluded.updated_at""", [
                (self.model_name, chunk_id, text_hash, batch_dimension,
                 self._pack(vector), now, now)
                for chunk_id, text_hash, vector in prepared
            ])
        self._run(write, write=True)

    def save(self) -> None:
        return None

    def snapshot(self, current_ids: set[str] | Mapping[str, str] | None = None) -> dict:
        current = _current_key_map(current_ids)

        def read(connection: sqlite3.Connection):
            count = int(connection.execute(
                "SELECT COUNT(*) FROM rag_embedding_cache WHERE model_name=?",
                (self.model_name,),
            ).fetchone()[0])
            dimension = self._dimension(connection)
            current_count = 0
            if current:
                for chunk_id, text_hash in current.items():
                    row = connection.execute(
                        "SELECT text_hash FROM rag_embedding_cache WHERE model_name=? AND chunk_id=?",
                        (self.model_name, chunk_id),
                    ).fetchone()
                    if row and (text_hash is None or row[0] == text_hash):
                        current_count += 1
            else:
                current_count = count
            return count, dimension, current_count
        count, dimension, current_count = self._run(read)
        return {
            "format": "sqlite", "path": str(self.path), "model": self.model_name,
            "exists": self.path.is_file(),
            "bytes": self.path.stat().st_size if self.path.is_file() else 0,
            "entries": count, "dimension": dimension,
            "current_entries": current_count,
            "missing_current_entries": max(0, len(current) - current_count),
            "stale_entries": max(0, count - current_count) if current else 0,
        }

    def prune(self, valid_ids: set[str]) -> int:
        valid = {str(value) for value in valid_ids}

        def write(connection: sqlite3.Connection):
            if not valid:
                cursor = connection.execute(
                    "DELETE FROM rag_embedding_cache WHERE model_name=?", (self.model_name,)
                )
                return cursor.rowcount
            removed = 0
            rows = [row[0] for row in connection.execute(
                "SELECT chunk_id FROM rag_embedding_cache WHERE model_name=?",
                (self.model_name,),
            )]
            stale = [value for value in rows if value not in valid]
            for start in range(0, len(stale), self._IN_BATCH_SIZE):
                batch = stale[start:start + self._IN_BATCH_SIZE]
                placeholders = ",".join("?" for _ in batch)
                cursor = connection.execute(
                    f"DELETE FROM rag_embedding_cache WHERE model_name=? "
                    f"AND chunk_id IN ({placeholders})", (self.model_name, *batch),
                )
                removed += cursor.rowcount
            return removed
        return int(self._run(write, write=True))

    def clear_model(self) -> int:
        def write(connection: sqlite3.Connection):
            cursor = connection.execute(
                "DELETE FROM rag_embedding_cache WHERE model_name=?", (self.model_name,)
            )
            now = time.time()
            connection.execute("""INSERT INTO rag_embedding_cache_meta(
                model_name,dimension,backend,updated_at,cleared
            ) VALUES(?,NULL,'sqlite',?,1) ON CONFLICT(model_name) DO UPDATE SET
                dimension=NULL,updated_at=excluded.updated_at,cleared=1""",
                (self.model_name, now),
            )
            return cursor.rowcount
        return int(self._run(write, write=True))

    def list_namespaces(self) -> list[dict]:
        def read(connection: sqlite3.Connection):
            return [dict(model=row[0], dimension=row[1], entries=int(row[2]),
                         last_updated=row[3], cleared=bool(row[4]))
                    for row in connection.execute("""SELECT m.model_name,m.dimension,
                        COUNT(c.chunk_id),m.updated_at,m.cleared
                        FROM rag_embedding_cache_meta m LEFT JOIN rag_embedding_cache c
                        ON c.model_name=m.model_name GROUP BY m.model_name
                        ORDER BY m.model_name""")]
        return self._run(read)

    def clear_namespaces(self, names: Iterable[str]) -> int:
        values = {names.strip()} if isinstance(names, str) else {
            str(name).strip() for name in names if str(name).strip()
        }
        if not values:
            return 0

        def write(connection: sqlite3.Connection):
            removed = 0
            for name in values:
                removed += connection.execute(
                    "DELETE FROM rag_embedding_cache WHERE model_name=?", (name,)
                ).rowcount
                connection.execute(
                    "DELETE FROM rag_embedding_cache_meta WHERE model_name=?", (name,)
                )
            return removed
        return int(self._run(write, write=True))

    def clear_old_namespaces(
        self, *, keep_models: Iterable[str] = (), max_age_seconds: float = 0.0,
        namespace_prefix: str | None = None,
    ) -> int:
        age = float(max_age_seconds)
        if not math.isfinite(age) or age < 0:
            raise EmbeddingCacheError("缓存命名空间保留时间无效")
        keep = {str(value) for value in keep_models}
        cutoff = time.time() - age

        def write(connection: sqlite3.Connection):
            rows = connection.execute(
                "SELECT model_name FROM rag_embedding_cache_meta WHERE updated_at<=?",
                (cutoff,),
            ).fetchall()
            names = [row[0] for row in rows if row[0] not in keep and (
                namespace_prefix is None or row[0].startswith(namespace_prefix)
            )]
            removed = 0
            for name in names:
                removed += connection.execute(
                    "DELETE FROM rag_embedding_cache WHERE model_name=?", (name,)
                ).rowcount
                connection.execute(
                    "DELETE FROM rag_embedding_cache_meta WHERE model_name=?", (name,)
                )
            return removed
        return int(self._run(write, write=True))

    def _migrate_legacy_json(self) -> None:
        legacy_path = self.path.with_suffix(".json")
        if not legacy_path.is_file():
            return

        def state(connection: sqlite3.Connection):
            row = connection.execute(
                "SELECT cleared FROM rag_embedding_cache_meta WHERE model_name=?",
                (self.model_name,),
            ).fetchone()
            count = connection.execute(
                "SELECT COUNT(*) FROM rag_embedding_cache WHERE model_name=?",
                (self.model_name,),
            ).fetchone()[0]
            return bool(row and row[0]), int(count)
        cleared, count = self._run(state)
        if cleared or count:
            return
        entries, _ = _JsonEmbeddingCache._read(legacy_path, self.model_name)
        self.put_many(
            (chunk_id, item["text_hash"], item["vector"])
            for chunk_id, item in entries.items()
        )

    def maintenance(
        self, *, valid_ids: set[str] | None = None,
        keep_models: Iterable[str] = (), namespace_max_age_seconds: float | None = None,
        namespace_prefix: str | None = None, checkpoint_mode: str = "PASSIVE",
        vacuum: bool = False,
    ) -> dict:
        pruned = self.prune(valid_ids) if valid_ids is not None else 0
        removed = self.clear_old_namespaces(
            keep_models=keep_models, max_age_seconds=namespace_max_age_seconds,
            namespace_prefix=namespace_prefix,
        ) if namespace_max_age_seconds is not None else 0
        checkpoint = self.checkpoint(checkpoint_mode)
        if vacuum:
            self._run(lambda connection: connection.execute("VACUUM"))
        return {
            "backend": "sqlite", "pruned_entries": pruned,
            "removed_namespace_entries": removed, "checkpoint": checkpoint,
            "vacuum": bool(vacuum), "snapshot": self.snapshot(),
        }

    def health(self, current_ids: set[str] | Mapping[str, str] | None = None) -> dict:
        result = self.snapshot(current_ids)
        result.update({"backend": "sqlite-document", "namespace_count": len(self.list_namespaces())})
        return result


class QueryEmbeddingCache(_SQLiteBase):
    """TTL/capacity bounded SQLite cache with expiring cross-worker leases."""

    def __init__(
        self, path: str | Path, model_name: str, *, ttl_seconds: float = 300.0,
        max_entries: int = 4096, busy_timeout_ms: int = 15000,
        maintenance_interval_seconds: float = 60.0,
    ):
        super().__init__(Path(path), busy_timeout_ms=busy_timeout_ms)
        self.model_name = str(model_name)
        self.ttl_seconds = max(0.0, float(ttl_seconds))
        self.max_entries = max(1, int(max_entries))
        self.maintenance_interval_seconds = max(0.0, float(maintenance_interval_seconds))
        self._last_maintenance = time.monotonic()
        self._initialize()

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _initialize(self) -> None:
        def initialize(connection: sqlite3.Connection):
            connection.execute("""CREATE TABLE IF NOT EXISTS rag_query_embedding_cache (
                model_name TEXT NOT NULL, query_hash TEXT NOT NULL,
                dimension INTEGER NOT NULL, vector BLOB NOT NULL,
                created_at REAL NOT NULL, PRIMARY KEY(model_name,query_hash)
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS rag_query_embedding_cache_meta (
                model_name TEXT PRIMARY KEY, dimension INTEGER,
                created_at REAL NOT NULL, updated_at REAL NOT NULL
            )""")
            connection.execute("""CREATE TABLE IF NOT EXISTS rag_query_embedding_leases (
                model_name TEXT NOT NULL, query_hash TEXT NOT NULL, owner_id TEXT NOT NULL,
                expires_at REAL NOT NULL, PRIMARY KEY(model_name,query_hash)
            )""")
            connection.execute("""CREATE INDEX IF NOT EXISTS rag_query_access_idx
                ON rag_query_embedding_cache(model_name,created_at)""")
            connection.execute("""CREATE INDEX IF NOT EXISTS rag_query_lease_expiry_idx
                ON rag_query_embedding_leases(expires_at)""")
        self._run(initialize, write=True)

    def _maybe_maintenance(self) -> None:
        if self.maintenance_interval_seconds <= 0:
            return
        now = time.monotonic()
        if now - self._last_maintenance < self.maintenance_interval_seconds:
            return
        self._last_maintenance = now
        self.prune()

    def get_many(self, texts: Iterable[str]) -> dict[str, list[float]]:
        self._maybe_maintenance()
        unique = list(dict.fromkeys(str(text) for text in texts))
        if not unique:
            return {}
        now = time.time()
        cutoff = now - self.ttl_seconds if self.ttl_seconds > 0 else None

        hashes = {self._hash(text): text for text in unique}

        def read(connection: sqlite3.Connection):
            result = {}
            values = list(hashes)
            for start in range(0, len(values), self._IN_BATCH_SIZE):
                batch = values[start:start + self._IN_BATCH_SIZE]
                placeholders = ",".join("?" for _ in batch)
                rows = connection.execute(
                    f"SELECT query_hash,dimension,vector,created_at "
                    f"FROM rag_query_embedding_cache WHERE model_name=? "
                    f"AND query_hash IN ({placeholders})",
                    (self.model_name, *batch),
                )
                for query_hash, dimension, blob, created_at in rows:
                    if cutoff is not None and created_at < cutoff:
                        continue
                    vector = self._unpack(blob, int(dimension))
                    text = hashes.get(query_hash)
                    if vector is not None and text is not None:
                        result[text] = vector
            return result
        return self._run(read)

    def put_many(self, values: Iterable[tuple[str, list[float]]]) -> None:
        self._maybe_maintenance()
        prepared = []
        dimension = None
        for text, vector in values:
            checked = _valid_vector(vector)
            if checked is None:
                raise EmbeddingCacheError("不能缓存空查询向量或非有限向量")
            dimension = dimension or len(checked)
            if len(checked) != dimension:
                raise EmbeddingCacheError("查询向量维度不一致")
            prepared.append((str(text), checked))
        if not prepared:
            return

        def write(connection: sqlite3.Connection):
            row = connection.execute(
                "SELECT dimension FROM rag_query_embedding_cache_meta WHERE model_name=?",
                (self.model_name,),
            ).fetchone()
            if row and row[0] and int(row[0]) != dimension:
                raise ValueError("查询缓存命名空间的向量维度不一致")
            now = time.time()
            connection.execute("""INSERT INTO rag_query_embedding_cache_meta(
                model_name,dimension,created_at,updated_at) VALUES(?,?,?,?)
                ON CONFLICT(model_name) DO UPDATE SET dimension=excluded.dimension,
                updated_at=excluded.updated_at""", (self.model_name, dimension, now, now))
            connection.executemany("""INSERT INTO rag_query_embedding_cache(
                model_name,query_hash,dimension,vector,created_at
            ) VALUES(?,?,?,?,?) ON CONFLICT(model_name,query_hash) DO UPDATE SET
                dimension=excluded.dimension,vector=excluded.vector,
                created_at=excluded.created_at""", [
                (self.model_name, self._hash(text), dimension,
                 self._pack(vector), now + index * 0.000001)
                for index, (text, vector) in enumerate(prepared)
            ])
            overflow = int(connection.execute(
                "SELECT COUNT(*) FROM rag_query_embedding_cache WHERE model_name=?",
                (self.model_name,),
            ).fetchone()[0]) - self.max_entries
            if overflow > 0:
                connection.execute("""DELETE FROM rag_query_embedding_cache WHERE rowid IN (
                    SELECT rowid FROM rag_query_embedding_cache WHERE model_name=?
                    ORDER BY created_at ASC, rowid ASC LIMIT ?
                )""", (self.model_name, overflow))
        self._run(write, write=True)

    def try_acquire_leases(
        self, texts: Iterable[str], owner_id: str, *, lease_seconds: float = 120.0,
    ) -> set[str]:
        unique = list(dict.fromkeys(str(text) for text in texts))
        if not unique:
            return set()
        now = time.time()
        expires = now + max(0.001, float(lease_seconds))

        def write(connection: sqlite3.Connection):
            connection.execute("DELETE FROM rag_query_embedding_leases WHERE expires_at<=?", (now,))
            acquired = set()
            for text in unique:
                query_hash = self._hash(text)
                connection.execute("""INSERT OR IGNORE INTO rag_query_embedding_leases(
                    model_name,query_hash,owner_id,expires_at) VALUES(?,?,?,?)""",
                    (self.model_name, query_hash, owner_id, expires),
                )
                row = connection.execute("""SELECT owner_id FROM rag_query_embedding_leases
                    WHERE model_name=? AND query_hash=?""",
                    (self.model_name, query_hash),
                ).fetchone()
                if row and row[0] == owner_id:
                    acquired.add(text)
            return acquired
        return self._run(write, write=True)

    def release_leases(self, texts: Iterable[str], owner_id: str) -> int:
        hashes = [self._hash(str(text)) for text in texts]
        if not hashes:
            return 0

        def write(connection: sqlite3.Connection):
            removed = 0
            for start in range(0, len(hashes), self._IN_BATCH_SIZE):
                batch = hashes[start:start + self._IN_BATCH_SIZE]
                placeholders = ",".join("?" for _ in batch)
                removed += connection.execute(
                    f"DELETE FROM rag_query_embedding_leases WHERE model_name=? "
                    f"AND owner_id=? AND query_hash IN ({placeholders})",
                    (self.model_name, owner_id, *batch),
                ).rowcount
            return removed
        return int(self._run(write, write=True))

    def prune(self) -> int:
        cutoff = time.time() - self.ttl_seconds if self.ttl_seconds > 0 else None

        def write(connection: sqlite3.Connection):
            removed = 0
            if cutoff is not None:
                removed += connection.execute("""DELETE FROM rag_query_embedding_cache
                    WHERE model_name=? AND created_at<?""", (self.model_name, cutoff)).rowcount
            overflow = int(connection.execute(
                "SELECT COUNT(*) FROM rag_query_embedding_cache WHERE model_name=?",
                (self.model_name,),
            ).fetchone()[0]) - self.max_entries
            if overflow > 0:
                removed += connection.execute("""DELETE FROM rag_query_embedding_cache WHERE rowid IN (
                    SELECT rowid FROM rag_query_embedding_cache WHERE model_name=?
                    ORDER BY created_at ASC, rowid ASC LIMIT ?
                )""", (self.model_name, overflow)).rowcount
            connection.execute("DELETE FROM rag_query_embedding_leases WHERE expires_at<=?", (time.time(),))
            return removed
        return int(self._run(write, write=True))

    def clear_model(self) -> int:
        def write(connection: sqlite3.Connection):
            count = connection.execute(
                "DELETE FROM rag_query_embedding_cache WHERE model_name=?", (self.model_name,)
            ).rowcount
            connection.execute(
                "DELETE FROM rag_query_embedding_leases WHERE model_name=?", (self.model_name,)
            )
            connection.execute(
                "DELETE FROM rag_query_embedding_cache_meta WHERE model_name=?", (self.model_name,)
            )
            return count
        return int(self._run(write, write=True))

    def snapshot(self, required_texts: Iterable[str] = ()) -> dict:
        now = time.time()
        cutoff = now - self.ttl_seconds if self.ttl_seconds > 0 else None

        def read(connection: sqlite3.Connection):
            entries = int(connection.execute(
                "SELECT COUNT(*) FROM rag_query_embedding_cache WHERE model_name=?",
                (self.model_name,),
            ).fetchone()[0])
            expired = int(connection.execute(
                "SELECT COUNT(*) FROM rag_query_embedding_cache WHERE model_name=? AND created_at<?",
                (self.model_name, cutoff),
            ).fetchone()[0]) if cutoff is not None else 0
            row = connection.execute(
                "SELECT dimension FROM rag_query_embedding_cache_meta WHERE model_name=?",
                (self.model_name,),
            ).fetchone()
            return entries, expired, (int(row[0]) if row and row[0] else None)
        entries, expired, dimension = self._run(read)
        required = list(dict.fromkeys(str(text) for text in required_texts))
        present = len(self.get_many(required)) if required else 0
        return {
            "format": "sqlite", "backend": "sqlite-query", "path": str(self.path),
            "model": self.model_name, "entries": entries, "expired_entries": expired,
            "dimension": dimension, "max_entries": self.max_entries,
            "ttl_seconds": self.ttl_seconds, "required_entries": present,
            "missing_required_entries": max(0, len(required) - present),
        }

    def health(self, required_texts: Iterable[str] = ()) -> dict:
        return self.snapshot(required_texts)

    def list_namespaces(self) -> list[dict]:
        return self._run(lambda connection: [
            {"model": row[0], "dimension": row[1], "entries": int(row[2]),
             "last_updated": row[3]}
            for row in connection.execute("""SELECT m.model_name,m.dimension,
                COUNT(c.query_hash),m.updated_at FROM rag_query_embedding_cache_meta m
                LEFT JOIN rag_query_embedding_cache c ON c.model_name=m.model_name
                GROUP BY m.model_name ORDER BY m.model_name""")
        ])

    def clear_namespaces(self, names: Iterable[str]) -> int:
        values = {names.strip()} if isinstance(names, str) else {
            str(name).strip() for name in names if str(name).strip()
        }
        if not values:
            return 0

        def write(connection: sqlite3.Connection):
            removed = 0
            for name in values:
                removed += connection.execute(
                    "DELETE FROM rag_query_embedding_cache WHERE model_name=?", (name,)
                ).rowcount
                connection.execute(
                    "DELETE FROM rag_query_embedding_leases WHERE model_name=?", (name,)
                )
                connection.execute(
                    "DELETE FROM rag_query_embedding_cache_meta WHERE model_name=?", (name,)
                )
            return removed
        return int(self._run(write, write=True))

    def clear_old_namespaces(
        self, *, keep_models: Iterable[str] = (), max_age_seconds: float = 0.0,
        namespace_prefix: str | None = None,
    ) -> int:
        keep = {str(value) for value in keep_models}
        cutoff = time.time() - max(0.0, float(max_age_seconds))
        names = [item["model"] for item in self.list_namespaces()
                 if item["model"] not in keep and item["last_updated"] <= cutoff and (
                     namespace_prefix is None or item["model"].startswith(namespace_prefix)
                 )]
        return self.clear_namespaces(names)

    def maintenance(
        self, *, keep_models: Iterable[str] = (),
        namespace_max_age_seconds: float | None = None,
        namespace_prefix: str | None = None, checkpoint_mode: str = "PASSIVE",
        vacuum: bool = False,
    ) -> dict:
        pruned = self.prune()
        removed = self.clear_old_namespaces(
            keep_models=keep_models, max_age_seconds=namespace_max_age_seconds,
            namespace_prefix=namespace_prefix,
        ) if namespace_max_age_seconds is not None else 0
        checkpoint = self.checkpoint(checkpoint_mode)
        if vacuum:
            self._run(lambda connection: connection.execute("VACUUM"))
        return {
            "backend": "sqlite-query", "pruned_entries": pruned,
            "removed_namespace_entries": removed, "checkpoint": checkpoint,
            "vacuum": bool(vacuum), "snapshot": self.snapshot(),
        }


class EmbeddingCache:
    """Facade selecting JSON compatibility or SQLite/WAL by file suffix."""

    def __init__(
        self, path: str | Path, model_name: str, *, migrate_legacy: bool = True,
        busy_timeout_ms: int = 15000,
    ):
        resolved = Path(path)
        if resolved.suffix.lower() == ".json":
            self._backend = _JsonEmbeddingCache(resolved, str(model_name))
        else:
            self._backend = _SQLiteEmbeddingCache(
                resolved, str(model_name), busy_timeout_ms=busy_timeout_ms,
                migrate_json=migrate_legacy,
            )

    @property
    def path(self) -> Path:
        return self._backend.path

    @property
    def model_name(self) -> str:
        return self._backend.model_name

    @property
    def entries(self) -> dict:
        return getattr(self._backend, "entries", {})

    @property
    def format(self) -> str:
        return "json" if isinstance(self._backend, _JsonEmbeddingCache) else "sqlite"

    def get(self, chunk_id: str, text_hash: str) -> list[float] | None:
        return self._backend.get(chunk_id, text_hash)

    def get_many(self, keys: Iterable[tuple[str, str]]) -> dict[str, list[float]]:
        return self._backend.get_many(keys)

    def put(self, chunk_id: str, text_hash: str, vector: list[float]) -> None:
        self._backend.put(chunk_id, text_hash, vector)

    def put_many(self, values: Iterable[tuple[str, str, list[float]]]) -> None:
        self._backend.put_many(values)

    def save(self) -> None:
        self._backend.save()

    def snapshot(self, current_ids=None) -> dict:
        return self._backend.snapshot(current_ids)

    def prune(self, valid_ids: set[str]) -> int:
        return self._backend.prune(valid_ids)

    def clear_model(self) -> int:
        return self._backend.clear_model()

    def list_namespaces(self) -> list[dict]:
        return self._backend.list_namespaces()

    def clear_namespaces(self, names: Iterable[str]) -> int:
        return self._backend.clear_namespaces(names)

    def clear_namespace(self, name: str) -> int:
        return self.clear_namespaces([name])

    def checkpoint(self, mode: str = "PASSIVE") -> dict:
        return self._backend.checkpoint(mode)

    def maintenance(self, **kwargs) -> dict:
        return self._backend.maintenance(**kwargs)

    def health(self, current_ids=None) -> dict:
        return self._backend.health(current_ids)

    def close(self) -> None:
        self._backend.close()
