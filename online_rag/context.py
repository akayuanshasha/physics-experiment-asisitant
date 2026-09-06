"""Turn ranked retrieval hits into a compact, cited evidence package."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from .models import Chunk, RetrievalHit


@dataclass(frozen=True)
class ContextConfig:
    max_evidence: int = 6
    max_context_chars: int = 8000
    max_chunks_per_experiment: int = 6
    duplicate_similarity: float = 0.92


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    chunk: Chunk
    retrieval_score: float
    truncated: bool = False
    context_relation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.evidence_id,
            "experiment_id": self.chunk.experiment_id,
            "experiment_name": self.chunk.experiment_name,
            "section": self.chunk.section,
            "page_start": self.chunk.page_start,
            "page_end": self.chunk.page_end,
            "source": self.chunk.source,
            "source_tier": self.chunk.source_tier,
            "source_kind": self.chunk.source_kind,
            "authority": self.chunk.authority,
            "is_example_data": self.chunk.is_example_data,
            "chunk_id": self.chunk.chunk_id,
            "parent_id": self.chunk.parent_id,
            "context_relation": self.context_relation,
            "retrieval_score": self.retrieval_score,
            "truncated": self.truncated,
        }


@dataclass
class ContextPackage:
    text: str
    evidence: list[Evidence]
    warnings: list[str] = field(default_factory=list)


def _normalized_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def _is_duplicate(chunk: Chunk, selected: list[Chunk], threshold: float) -> bool:
    candidate = _normalized_text(chunk.text)
    for previous in selected:
        if chunk.chunk_id == previous.chunk_id:
            return True
        if (
            chunk.experiment_id != previous.experiment_id
            or chunk.section != previous.section
        ):
            continue
        existing = _normalized_text(previous.text)
        if not candidate or not existing:
            continue
        shorter, longer = sorted((candidate, existing), key=len)
        if len(shorter) >= 80 and shorter in longer:
            return True
        if SequenceMatcher(None, candidate, existing, autojunk=False).ratio() >= threshold:
            return True
    return False


def _page_label(chunk: Chunk) -> str:
    if chunk.page_start is None:
        return "未知"
    if chunk.page_end is None or chunk.page_end == chunk.page_start:
        return str(chunk.page_start)
    return f"{chunk.page_start}-{chunk.page_end}"


def _header(evidence_id: str, chunk: Chunk, context_relation: str | None = None) -> str:
    relation = f"上下文关系：{context_relation}\n" if context_relation else ""
    return (
        f"[{evidence_id}]\n"
        f"实验：{chunk.experiment_name}\n"
        f"章节：{chunk.section}\n"
        f"页码：{_page_label(chunk)}\n"
        f"源文件：{chunk.source}\n"
        f"资料等级：{chunk.source_tier}\n"
        f"资料类型：{chunk.source_kind}\n"
        f"{relation}"
        "内容："
    )


def build_context(
    hits: list[RetrievalHit], config: ContextConfig | None = None,
) -> ContextPackage:
    """Select, deduplicate and label evidence while respecting a hard char budget."""
    cfg = config or ContextConfig()
    if cfg.max_evidence <= 0 or cfg.max_context_chars <= 0:
        return ContextPackage("", [], ["上下文配置不允许加入证据"])

    blocks: list[str] = []
    evidence: list[Evidence] = []
    selected_chunks: list[Chunk] = []
    per_experiment: Counter[str] = Counter()
    duplicate_count = 0
    limited_count = 0

    for hit in hits:
        if len(evidence) >= cfg.max_evidence:
            break
        chunk = hit.chunk
        if per_experiment[chunk.experiment_id] >= cfg.max_chunks_per_experiment:
            limited_count += 1
            continue
        if _is_duplicate(chunk, selected_chunks, cfg.duplicate_similarity):
            duplicate_count += 1
            continue

        evidence_id = f"E{len(evidence) + 1}"
        separator = "\n\n" if blocks else ""
        header = _header(evidence_id, chunk, hit.context_relation)
        used = sum(len(block) for block in blocks)
        remaining = cfg.max_context_chars - used - len(separator)
        available_text = remaining - len(header)
        if available_text <= 0:
            break

        content = chunk.text.strip()
        truncated = len(content) > available_text
        if truncated:
            if available_text == 1:
                content = "…"
            else:
                content = content[:available_text - 1].rstrip() + "…"
        block = separator + header + content
        blocks.append(block)
        selected_chunks.append(chunk)
        per_experiment[chunk.experiment_id] += 1
        evidence.append(Evidence(
            evidence_id, chunk, hit.score, truncated, hit.context_relation,
        ))

    warnings: list[str] = []
    if duplicate_count:
        warnings.append(f"已跳过 {duplicate_count} 条重复证据")
    if limited_count:
        warnings.append(f"已跳过 {limited_count} 条过度集中的同实验证据")
    if hits and not evidence:
        warnings.append("检索结果无法放入当前上下文预算")
    return ContextPackage("".join(blocks), evidence, warnings)
