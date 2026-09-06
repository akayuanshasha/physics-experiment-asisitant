"""Rewrite context-dependent follow-up questions before retrieval."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .chat import ChatBackend


_CONTEXT_REFERENCE_RE = re.compile(
    r"(?:^|[，。！？?\s])(?:那|那么|它|它们|这个|这些|该实验|上述|前面|其中|"
    r"这一步|这个公式|该怎么|还有|然后)"
)
_VAGUE_FOLLOW_UP_RE = re.compile(
    r"^(?:为什么|为什么呢|怎么做|怎么算|怎么办|还有吗|还有呢|然后呢|"
    r"具体呢|下一步呢)[？?。！!\s]*$"
)


@dataclass(frozen=True)
class RewriteResult:
    question: str
    rewritten: bool = False
    warning: str | None = None


class HistoryQuestionRewriter:
    """Use the chat backend only when a question appears to depend on history."""

    def __init__(self, chat_backend: ChatBackend, *, max_history_messages: int = 6):
        self.chat_backend = chat_backend
        self.max_history_messages = max(1, max_history_messages)

    @staticmethod
    def _clean_history(history: Iterable[dict] | None) -> list[dict[str, str]]:
        cleaned: list[dict[str, str]] = []
        for item in history or []:
            if not isinstance(item, dict):
                continue
            role = item.get("role")
            content = str(item.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                cleaned.append({"role": role, "content": content})
        return cleaned

    @classmethod
    def needs_rewrite(cls, question: str, history: Iterable[dict] | None) -> bool:
        cleaned = cls._clean_history(history)
        if not cleaned:
            return False
        text = str(question or "").strip()
        if not text:
            return False
        return bool(_CONTEXT_REFERENCE_RE.search(text)) or bool(
            _VAGUE_FOLLOW_UP_RE.fullmatch(text)
        )

    @staticmethod
    def _fallback(question: str, history: list[dict[str, str]]) -> str:
        previous = next(
            (item["content"] for item in reversed(history) if item["role"] == "user"),
            "",
        )
        return f"关于前一个问题“{previous[:180]}”，学生继续问：{question}" if previous else question

    def rewrite(
        self, question: str, history: Iterable[dict] | None = None,
    ) -> RewriteResult:
        original = str(question or "").strip()
        cleaned = self._clean_history(history)[-self.max_history_messages:]
        if not self.needs_rewrite(original, cleaned):
            return RewriteResult(original)

        transcript = "\n".join(
            f"{'学生' if item['role'] == 'user' else '助教'}：{item['content']}"
            for item in cleaned
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "把学生的当前追问改写成无需对话历史也能独立理解的大学物理实验问题。"
                    "保留原意、实验名、符号和限制；不要回答问题，只输出改写后的一个问题。"
                ),
            },
            {
                "role": "user",
                "content": f"对话历史：\n{transcript}\n\n当前追问：\n{original}",
            },
        ]
        try:
            rewritten = self.chat_backend.complete(
                messages, temperature=0.0, max_tokens=256,
            ).strip().strip('"“”')
            if not rewritten or len(rewritten) > 500:
                raise ValueError("改写结果为空或过长")
            return RewriteResult(rewritten, rewritten=rewritten != original)
        except Exception as exc:
            return RewriteResult(
                self._fallback(original, cleaned),
                rewritten=True,
                warning=f"历史问题模型改写失败，已使用确定性回退：{type(exc).__name__}",
            )
