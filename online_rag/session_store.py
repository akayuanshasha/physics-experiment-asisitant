"""SQLite-default, Redis-optional persistent conversation storage."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import threading
import time
from typing import Protocol
from contextlib import contextmanager


class SessionStore(Protocol):
    def get(self, user_id: str, session_id: str) -> list[dict]: ...
    def set(self, user_id: str, session_id: str, messages: list[dict]) -> None: ...
    def delete(self, user_id: str, session_id: str) -> None: ...


class SQLiteSessionStore:
    def __init__(
        self,
        path: str | Path = ".cache/online_rag/sessions.sqlite3",
        *,
        ttl_seconds: int = 86400,
        cleanup_interval_seconds: float = 300.0,
    ):
        self.path = Path(path)
        self.ttl_seconds = max(0, int(ttl_seconds))
        self.cleanup_interval_seconds = max(0.0, float(cleanup_interval_seconds))
        self._last_cleanup_at = 0.0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5.0)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    @contextmanager
    def _connection(self):
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connection() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS rag_sessions (
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    messages_json TEXT NOT NULL,
                    updated_at REAL NOT NULL,
                    PRIMARY KEY (user_id, session_id)
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_rag_sessions_updated_at "
                "ON rag_sessions(updated_at)"
            )

    def _cleanup_expired(self, connection, *, now: float, force: bool = False) -> None:
        if self.ttl_seconds <= 0:
            return
        monotonic_now = time.monotonic()
        if not force and (
            monotonic_now - self._last_cleanup_at < self.cleanup_interval_seconds
        ):
            return
        connection.execute(
            "DELETE FROM rag_sessions WHERE updated_at < ?",
            (now - self.ttl_seconds,),
        )
        self._last_cleanup_at = monotonic_now

    def get(self, user_id: str, session_id: str) -> list[dict]:
        with self._lock, self._connection() as connection:
            row = connection.execute(
                "SELECT messages_json, updated_at FROM rag_sessions "
                "WHERE user_id=? AND session_id=?",
                (user_id, session_id),
            ).fetchone()
            now = time.time()
            if row and self.ttl_seconds > 0 and row[1] < now - self.ttl_seconds:
                connection.execute(
                    "DELETE FROM rag_sessions WHERE user_id=? AND session_id=?",
                    (user_id, session_id),
                )
                row = None
            self._cleanup_expired(connection, now=now)
        if not row:
            return []
        try:
            value = json.loads(row[0])
        except json.JSONDecodeError:
            return []
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    def set(self, user_id: str, session_id: str, messages: list[dict]) -> None:
        payload = json.dumps(messages, ensure_ascii=False)
        with self._lock, self._connection() as connection:
            now = time.time()
            connection.execute(
                """INSERT INTO rag_sessions(user_id, session_id, messages_json, updated_at)
                   VALUES(?, ?, ?, ?)
                   ON CONFLICT(user_id, session_id) DO UPDATE SET
                   messages_json=excluded.messages_json,
                   updated_at=excluded.updated_at""",
                (user_id, session_id, payload, now),
            )
            self._cleanup_expired(connection, now=now)

    def delete(self, user_id: str, session_id: str) -> None:
        with self._lock, self._connection() as connection:
            connection.execute(
                "DELETE FROM rag_sessions WHERE user_id=? AND session_id=?",
                (user_id, session_id),
            )


class RedisSessionStore:
    def __init__(self, url: str, *, ttl_seconds: int = 86400):
        try:
            import redis
        except ImportError as exc:
            raise RuntimeError("配置了 REDIS_URL，但未安装 redis Python 包") from exc
        self.client = redis.Redis.from_url(url, decode_responses=True)
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _key(user_id: str, session_id: str) -> str:
        return f"physics-rag:session:{user_id}:{session_id}"

    def get(self, user_id: str, session_id: str) -> list[dict]:
        raw = self.client.get(self._key(user_id, session_id))
        if not raw:
            return []
        value = json.loads(raw)
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    def set(self, user_id: str, session_id: str, messages: list[dict]) -> None:
        self.client.setex(
            self._key(user_id, session_id),
            self.ttl_seconds,
            json.dumps(messages, ensure_ascii=False),
        )

    def delete(self, user_id: str, session_id: str) -> None:
        self.client.delete(self._key(user_id, session_id))


def create_session_store_from_env() -> SessionStore:
    redis_url = os.getenv("REDIS_URL", "").strip()
    ttl = int(os.getenv("RAG_SESSION_TTL_SECONDS", "86400"))
    if redis_url:
        return RedisSessionStore(redis_url, ttl_seconds=ttl)
    return SQLiteSessionStore(os.getenv(
        "RAG_SESSION_DB", ".cache/online_rag/sessions.sqlite3"
    ), ttl_seconds=ttl)
