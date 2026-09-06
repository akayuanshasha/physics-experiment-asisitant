"""Privacy-conscious structured diagnostics for the RAG request path."""

from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path
import threading
import time
from typing import Any


def anonymous_id(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


class RagDiagnostics:
    def __init__(
        self,
        path: str | Path = ".cache/online_rag/rag_events.jsonl",
        *,
        memory_limit: int = 200,
    ):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._recent = deque(maxlen=memory_limit)
        self._lock = threading.RLock()

    def record(self, event: dict[str, Any]) -> dict[str, Any]:
        row = dict(event)
        row.setdefault("timestamp", time.time())
        encoded = json.dumps(row, ensure_ascii=False, allow_nan=False)
        with self._lock:
            self._recent.append(row)
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(encoded + "\n")
        return row

    def find(self, request_id: str) -> dict[str, Any] | None:
        with self._lock:
            return next(
                (dict(item) for item in reversed(self._recent)
                 if item.get("request_id") == request_id),
                None,
            )
